// =============================================================================
// /api/upload  — POST handler
//
// VERCEL DEPLOYMENT NOTE
// ──────────────────────
// This route previously spawned `python predict.py` as a child_process after
// uploading the CSV to Supabase. That step has been removed because Vercel
// serverless functions cannot run Python subprocesses or access local .pkl
// model files.
//
// What changed:
//   • Supabase CSV upload + DB metadata insert — UNCHANGED (runs on Vercel).
//   • CSV parse + preprocess + aggregate calculation — UNCHANGED (pure TS).
//   • Python subprocess for ML predictions — REPLACED with fetch() to the
//     Render ML backend (POST /predict).
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
import { calculateDatasetAggregates, calculateTrends } from "@/lib/features";

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
    }

    if (!file.name.endsWith(".csv")) {
      return NextResponse.json({ error: "Only CSV files allowed" }, { status: 400 });
    }

    const fileName = `${Date.now()}-${file.name}`;
    const filePath = `uploads/${fileName}`;

    const arrayBuffer = await file.arrayBuffer();
    const buffer = new Uint8Array(arrayBuffer);

    // Upload to Supabase Storage (graceful — skip if Supabase is unreachable)
    try {
      const { error: uploadError } = await supabase.storage
        .from("wearable-uploads")
        .upload(filePath, buffer, {
          contentType: "text/csv",
          upsert: true,
        });

      if (uploadError) {
        console.warn("Supabase storage upload warning:", uploadError.message);
      } else {
        // Save metadata to DB table only if storage upload succeeded
        const { error: dbError } = await supabase.from("uploads").insert([
          {
            file_name: file.name,
            file_path: filePath,
          },
        ]);

        if (dbError) {
          console.warn("Supabase DB insert warning:", dbError.message);
        }
      }
    } catch (supabaseError) {
      console.warn("Supabase unavailable, processing file locally:", supabaseError);
    }

    // ========== PROCESS THE FILE ==========
    // Convert the uploaded file buffer to string for parsing
    const csvString = new TextDecoder().decode(buffer);

    // Parse CSV string
    const parseResult = parseCSVString(csvString);

    if (parseResult.errors.length > 0) {
      console.warn("CSV parsing warnings:", parseResult.errors);
    }

    // Preprocess data (this also normalizes column names to lowercase with underscores)
    const preprocessResult = preprocessData(parseResult.data, {
      removeNulls: true,
      trimStrings: true,
      normalizeKeys: true,
    });

    // Calculate dataset-level aggregates
    const aggregates = calculateDatasetAggregates(preprocessResult.data);
    
    // Calculate trends
    const trends = calculateTrends(preprocessResult.data);

    // Log aggregates for debugging
    console.log("Calculated aggregates:", JSON.stringify(aggregates, null, 2));

    // ── Call the Render ML service (replaces Python subprocess) ─────────────
    // Vercel cannot spawn child processes. ML inference runs on a separate
    // Python service (Flask/FastAPI) hosted on Render.
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

    return NextResponse.json({
      file: filePath,
      recordCount: preprocessResult.processed,
      skipped: preprocessResult.skipped,
      aggregates,
      trends, // Add trends to response
      predictions,
    });
  } catch (err: unknown) {
    console.error("API /upload error:", err);
    const errorMessage = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}
