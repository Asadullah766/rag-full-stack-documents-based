"use client";

import React, { useState } from "react";

export default function FileUploader() {
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [fileName, setFileName] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [processProgress, setProcessProgress] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isUploaded, setIsUploaded] = useState<boolean>(false);

  // ---------------- File Upload ----------------
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];

    setFileName(file.name);
    setUploadProgress(0);
    setUploadStatus("⏳ Uploading...");
    setIsUploaded(false);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("http://127.0.0.1:8000/ingest", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      // Simulate upload progress
      let progress = 0;
      const interval = setInterval(() => {
        progress += 20;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setUploadStatus("✅ Uploaded");
          setUploadProgress(0);
          setIsUploaded(true);
        } else {
          setUploadProgress(progress);
        }
      }, 150);
    } catch (err) {
      console.error(err);
      setUploadStatus("❌ Upload failed. Check backend.");
      setUploadProgress(0);
      setIsUploaded(false);
    }
  };

  // ---------------- Process (Polling Backend Status) ----------------
  const handleProcess = async () => {
    if (!fileName) {
      setUploadStatus("⚠️ Please upload a file first!");
      return;
    }

    setIsProcessing(true);
    setUploadStatus("🔄 Processing...");
    setProcessProgress(10);

    // Start polling backend for ingestion status
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/status/${fileName}`);
        const data = await res.json();

        if (data.status === "completed") {
          setUploadStatus("✅ Process completed");
          setProcessProgress(0);
          clearInterval(interval);
          setIsProcessing(false);
        } else if (data.status === "failed") {
          setUploadStatus("❌ Process failed");
          setProcessProgress(0);
          clearInterval(interval);
          setIsProcessing(false);
        } else {
          // Still processing
          setUploadStatus("⏳ Processing...");
          setProcessProgress((prev) => (prev < 90 ? prev + 10 : prev)); // smooth animation
        }
      } catch (err) {
        console.error(err);
        setUploadStatus("⚠️ Error checking process status");
      }
    }, 2000); // check every 2s
  };

  // ---------------- UI ----------------
  return (
    <div className="flex flex-col gap-4">
      {/* Upload Box */}
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

      {/* File Name */}
      {isUploaded && fileName && (
        <div className="flex justify-center">
          <span className="text-gray-700 dark:text-gray-200 font-medium truncate">
            {fileName}
          </span>
        </div>
      )}

      {/* Upload Progress */}
      {uploadProgress > 0 && (
        <div className="w-full bg-gray-300 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
          <div
            className="bg-blue-500 h-2 transition-all"
            style={{ width: `${uploadProgress}%` }}
          />
        </div>
      )}

      {/* Process Button */}
      {isUploaded && (
        <div className="flex justify-center mt-2">
          <button
            onClick={handleProcess}
            className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-xl"
            disabled={isProcessing}
          >
            {isProcessing ? "Processing..." : "Process"}
          </button>
        </div>
      )}

      {/* Process Progress */}
      {processProgress > 0 && (
        <div className="w-full bg-gray-300 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
          <div
            className="bg-green-500 h-2 transition-all"
            style={{ width: `${processProgress}%` }}
          />
        </div>
      )}

      {/* Status */}
      {uploadStatus && (
        <p className="text-sm text-gray-600 dark:text-gray-300 text-center mt-1">
          {uploadStatus}
        </p>
      )}
    </div>
  );
}
