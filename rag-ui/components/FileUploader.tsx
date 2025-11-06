"use client";

import React, { useState, useEffect } from "react";

interface FileUploaderProps {
  onProcessComplete?: () => void;
}

export default function FileUploader({ onProcessComplete }: FileUploaderProps) {
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [processProgress, setProcessProgress] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  // ---------------- Load files from localStorage ----------------
  useEffect(() => {
    const loadFiles = async () => {
      const savedFiles = localStorage.getItem("uploadedFiles");
      if (!savedFiles) return;

      const files: string[] = JSON.parse(savedFiles);
      const existingFiles: string[] = [];

      for (const fileName of files) {
        try {
          const res = await fetch(`http://127.0.0.1:8000/status/${fileName}`);
          if (res.status === 404) continue;
          const data = await res.json();
          if (data.status) existingFiles.push(fileName);
        } catch (err) {
          console.error(`Error checking ${fileName}:`, err);
        }
      }

      setUploadedFiles(existingFiles);
      localStorage.setItem("uploadedFiles", JSON.stringify(existingFiles));
    };

    loadFiles();
  }, []);

  useEffect(() => {
    localStorage.setItem("uploadedFiles", JSON.stringify(uploadedFiles));
  }, [uploadedFiles]);

  // ---------------- File Upload ----------------
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];

    if (uploadedFiles.includes(file.name)) {
      setUploadStatus(`⚠️ "${file.name}" already uploaded`);
      e.target.value = "";
      return;
    }

    setUploadStatus(`⏳ Uploading ${file.name}...`);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append("file", file);

      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "http://127.0.0.1:8000/ingest");

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            setUploadProgress(percent);
          }
        };

        xhr.onload = () => {
          if (xhr.status === 200) resolve();
          else reject(new Error("Upload failed"));
        };
        xhr.onerror = () => reject(new Error("Upload failed"));
        xhr.send(formData);
      });

      setUploadStatus(`✅ ${file.name} uploaded`);
      setUploadedFiles((prev) => [...prev, file.name]);
    } catch (err) {
      console.error(err);
      setUploadStatus("❌ Upload failed. Check backend.");
    } finally {
      setUploadProgress(0);
      e.target.value = "";
    }
  };

  // ---------------- Process All ----------------
  const handleProcess = async () => {
    if (uploadedFiles.length === 0) {
      setUploadStatus("⚠️ Please upload a file first!");
      return;
    }

    setIsProcessing(true);
    setProcessProgress(0);
    setUploadStatus("🔄 Processing...");

    const totalFiles = uploadedFiles.length;

    const interval = setInterval(async () => {
      try {
        const statuses = await Promise.all(
          uploadedFiles.map(async (fileName) => {
            try {
              const res = await fetch(`http://127.0.0.1:8000/status/${fileName}`);
              if (res.status === 404) {
                setUploadedFiles((prev) => prev.filter((f) => f !== fileName));
                return { fileName, status: "missing" };
              }
              const data = await res.json();
              return { fileName, status: data.status };
            } catch {
              return { fileName, status: "error" };
            }
          })
        );

        const validStatuses = statuses.filter((s) => s.status !== "missing");
        const completedCount = validStatuses.filter((s) => s.status === "completed").length;
        const anyFailed = validStatuses.some((s) => s.status === "failed");

        setProcessProgress(Math.round((completedCount / totalFiles) * 100));

        if (completedCount === totalFiles) {
          clearInterval(interval);
          setIsProcessing(false);
          setUploadStatus("✅ FILE PROCESSED SUCCESSFULLY!");

          // 🕒 5 sec baad message hide + ChatBox reset
          setTimeout(() => {
            setUploadStatus("");
            localStorage.setItem("resetChat", "true"); // 👈 trigger for ChatBox reset

            // ✅ Notify parent (page.tsx)
            if (onProcessComplete) onProcessComplete();
          }, 5000);
        } else if (anyFailed) {
          clearInterval(interval);
          setIsProcessing(false);
          setUploadStatus("❌ Some files failed to process");
        } else {
          setUploadStatus("⏳ Processing files...");
        }
      } catch (err) {
        console.error(err);
        setUploadStatus("⚠️ Error checking process status");
      }
    }, 2000);
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
        <input id="fileInput" type="file" className="hidden" onChange={handleFileChange} />
      </label>

      {/* Uploaded Files */}
      {uploadedFiles.length > 0 && (
        <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-xl">
          <p className="text-gray-600 dark:text-gray-300 font-semibold mb-2">
            📂 Uploaded Files
          </p>
          {uploadedFiles.map((file, index) => (
            <div key={index} className="flex items-center justify-between border-b border-gray-300 dark:border-gray-700 py-1">
              <span className="text-gray-700 dark:text-gray-200">{file}</span>
              <span className="text-green-500 text-lg">✔</span>
            </div>
          ))}
        </div>
      )}

      {/* Upload Progress */}
      {uploadProgress > 0 && (
        <div className="w-full bg-gray-300 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
          <div className="bg-blue-500 h-2 transition-all" style={{ width: `${uploadProgress}%` }} />
        </div>
      )}

      {/* Process Button */}
      {uploadedFiles.length > 0 && (
        <div className="flex justify-center mt-2">
          <button
            onClick={handleProcess}
            className="bg-green-500 hover:bg-green-600 text-white px-6 py-2 rounded-xl disabled:opacity-70"
            disabled={isProcessing}
          >
            {isProcessing ? "Processing..." : "PROCESS FILE"}
          </button>
        </div>
      )}

      {/* Process Progress */}
      {isProcessing && (
        <div className="w-full bg-gray-300 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
          <div className="bg-green-500 h-2 transition-all" style={{ width: `${processProgress}%` }} />
        </div>
      )}

      {/* Status Message */}
      {uploadStatus && (
        <p className="text-sm text-gray-600 dark:text-gray-300 text-center mt-1">{uploadStatus}</p>
      )}
    </div>
  );
}
