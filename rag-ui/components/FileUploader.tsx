"use client";

import React, { useState, useEffect } from "react";

export default function FileUploader() {
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [fileName, setFileName] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [processProgress, setProcessProgress] = useState<number>(0);
  const [processing, setProcessing] = useState<boolean>(false);

  // 🔹 Upload Function
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setFileName(file.name);

    const formData = new FormData();
    formData.append("file", file);

    setUploadStatus("⏳ Uploading...");
    setUploadProgress(0);

    try {
      const res = await fetch("http://127.0.0.1:8000/ingest", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();
      setUploadStatus("✅ File uploaded successfully!");
      setUploadProgress(100);

      console.log("Server:", data);
    } catch (err) {
      console.error(err);
      setUploadStatus("❌ Upload failed. Check backend.");
      setUploadProgress(0);
    }
  };

  // 🔹 Process Function
  const handleProcess = async () => {
    if (!fileName) {
      setUploadStatus("⚠️ Please upload a file first!");
      return;
    }

    setUploadStatus("🔄 Processing file...");
    setProcessProgress(0);
    setProcessing(true);

    // Poll backend for real progress
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/process/${fileName}`);
        if (!res.ok) throw new Error("Process failed");

        const data = await res.json();
        setProcessProgress(data.progress || 0);

        if (data.status === "done") {
          setUploadStatus("✅ Processing complete!");
          setProcessing(false);
          clearInterval(interval);
        } else if (data.status === "failed") {
          setUploadStatus("❌ Processing failed!");
          setProcessing(false);
          clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
        setUploadStatus("❌ Processing failed. Check backend.");
        setProcessing(false);
        clearInterval(interval);
      }
    }, 500); // Poll every 0.5s
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Upload */}
      <label
        htmlFor="fileInput"
        className="border-2 border-dashed border-gray-400 dark:border-gray-600 p-6 rounded-xl text-center cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition"
      >
        <p className="text-gray-500 dark:text-gray-300">
          Click or drag file to upload
        </p>
        <input
          id="fileInput"
          type="file"
          className="hidden"
          onChange={handleFileChange}
        />
      </label>

      {/* Upload Progress Bar */}
      {uploadProgress > 0 && (
        <div className="w-full bg-gray-200 dark:bg-gray-700 h-3 rounded-full overflow-hidden">
          <div
            className="bg-blue-600 h-3"
            style={{ width: `${uploadProgress}%`, transition: "width 0.2s" }}
          />
        </div>
      )}

      {/* Process Button */}
      <button
        onClick={handleProcess}
        className={`bg-blue-600 hover:bg-blue-700 text-white rounded-xl py-3 transition ${
          processing ? "opacity-50 cursor-not-allowed" : ""
        }`}
        disabled={processing}
      >
        ⚙️ Process File
      </button>

      {/* Process Progress Bar */}
      {processProgress > 0 && (
        <div className="w-full bg-gray-200 dark:bg-gray-700 h-3 rounded-full overflow-hidden">
          <div
            className="bg-green-500 h-3"
            style={{ width: `${processProgress}%`, transition: "width 0.2s" }}
          />
        </div>
      )}

      {/* Status */}
      {uploadStatus && (
        <p className="text-sm text-gray-600 dark:text-gray-300">{uploadStatus}</p>
      )}
    </div>
  );
}
