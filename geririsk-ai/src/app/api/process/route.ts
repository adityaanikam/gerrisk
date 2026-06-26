// =============================================================================
// /api/process  — GET handler
//
// VERCEL DEPLOYMENT NOTE
// ──────────────────────
// This route previously spawned `python predict.py` as a child_process to run
// ML inference locally. That approach is NOT compatible with Vercel serverless
// functions because:
//
//   1. Vercel functions run in an isolated Lambda environment — there is no
//      Python runtime, no filesystem access to .py / .pkl files, and
//      child_process.spawn() is blocked.
//   2. The ml/ directory and model .pkl files are never deployed to Vercel.
//
// SOLUTION — Render ML backend
// ─────────────────────────────
// The ML inference has been extracted to a standalone Python web service
// (Flask / FastAPI) hosted on Render. That service exposes:
//
//   POST /predict
//   Body: { avgHeartRate, maxHeartRate, minHeartRate, minSpO2, totalSteps, recordCount }
//   Returns: { cardiacRisk: {score, level}, fallRisk: {score, level}, respiratoryRisk: {score, level} }
//
// This route now:
//   1. Fetches + parses the latest CSV from Supabase Storage (unchanged).
//   2. Calculates aggregates in TypeScript (unchanged).
//   3. Calls the Render ML service via fetch() instead of spawning Python.
//
// Required environment variable (set in Vercel + .env.local):
//   ML_API_URL=https://your-service.onrender.com
//
// See ENV_SETUP.md for full configuration instructions.
// =============================================================================

export const runtime = "nodejs";

import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabaseClient";
import { parseCSVString } from "@/lib/csvParser";
import { preprocessData } from "@/lib/preprocess";
import { calculateDatasetAggregates } from "@/lib/features";

export async function GET() {
  try {
    // ── 1. Fetch latest uploaded file record from Supabase ──────────────────
    const { data: uploads, error } = await supabase
      .from("uploads")
      .select("*")
      .order("uploaded_at", { ascending: false })
      .limit(1);

    if (error || !uploads || uploads.length === 0) {
      return NextResponse.json({ error: "No uploads found" }, { status: 400 });
    }

    const filePath = uploads[0].file_path;

    // ── 2. Download CSV from Supabase Storage ───────────────────────────────
    const { data: fileData, error: downloadError } = await supabase.storage
      .from("wearable-uploads")
      .download(filePath);

    if (downloadError || !fileData) {
      return NextResponse.json(
        { error: "Failed to download file" },
        { status: 500 }
      );
    }

    // ── 3. Parse + preprocess ───────────────────────────────────────────────
    const csvString = await fileData.text();
    const parseResult = parseCSVString(csvString);

    if (parseResult.errors.length > 0) {
      return NextResponse.json(
        { error: "CSV parsing errors", details: parseResult.errors },
        { status: 400 }
      );
    }

    const preprocessResult = preprocessData(parseResult.data, {
      removeNulls: true,
      trimStrings: true,
      normalizeKeys: true,
    });

    // ── 4. Calculate aggregates (TypeScript — runs fine on Vercel) ──────────
    const aggregates = calculateDatasetAggregates(preprocessResult.data);

    // ── 5. Call the Render ML service instead of spawning Python ────────────
    const mlApiUrl = process.env.ML_API_URL;
    if (!mlApiUrl) {
      return NextResponse.json(
        {
          error:
            "ML_API_URL environment variable is not set. " +
            "See ENV_SETUP.md for configuration instructions.",
        },
        { status: 500 }
      );
    }

    const mlResponse = await fetch(`${mlApiUrl}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(aggregates),
    });

    if (!mlResponse.ok) {
      const mlError = await mlResponse.text();
      console.error("ML service error:", mlError);
      return NextResponse.json(
        { error: `ML service returned ${mlResponse.status}: ${mlError}` },
        { status: 502 }
      );
    }

    const predictions = await mlResponse.json();

    // ── 6. Return combined response ─────────────────────────────────────────
    return NextResponse.json({
      file: filePath,
      recordCount: preprocessResult.processed,
      skipped: preprocessResult.skipped,
      aggregates,
      predictions,
    });
  } catch (err: unknown) {
    console.error("API /process error:", err);
    const errorMessage = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
