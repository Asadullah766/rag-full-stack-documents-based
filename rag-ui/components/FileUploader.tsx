"use client";

import React, { useState } from "react";

export default function FileUploader() {
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [fileName, setFileName] = useState<string>("");

  // 🔹 Upload Function
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setFileName(file.name);

    const formData = new FormData();
    formData.append("file", file);

    setUploadStatus("⏳ Uploading...");
    try {
      const res = await fetch("http://127.0.0.1:8000/ingest", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");
      const data = await res.json();

      setUploadStatus("✅ File uploaded successfully!");
      console.log("Server:", data);
    } catch (err) {
      console.error(err);
      setUploadStatus("❌ Upload failed. Check backend.");
    }
  };

  // 🔹 Process Function
  const handleProcess = async () => {
    if (!fileName) {
      setUploadStatus("⚠️ Please upload a file first!");
      return;
    }

    setUploadStatus("🔄 Processing file...");
    try {
      const res = await fetch(`http://127.0.0.1:8000/process/${fileName}`, {
        method: "GET",
      });
      if (!res.ok) throw new Error("Process failed");

      const data = await res.json();
      setUploadStatus(`✅ Processing complete: ${data.status || "done"}`);
      console.log("Process:", data);
    } catch (err) {
      console.error(err);
      setUploadStatus("❌ Processing failed. Check backend.");
    }
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
        <input id="fileInput" type="file" className="hidden" onChange={handleFileChange} />
      </label>

      {/* Process Button */}
      <button
        onClick={handleProcess}
        className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl py-3 transition"
      >
        ⚙️ Process File
      </button>

      {/* Status */}
      {uploadStatus && (
        <p className="text-sm text-gray-600 dark:text-gray-300">{uploadStatus}</p>
      )}
    </div>
  );
}
