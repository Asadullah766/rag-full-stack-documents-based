"use client";

import React from "react";
import ThemeToggle from "./themetoggle";

const Navbar = () => {
  return (
    <nav className="bg-white dark:bg-gray-900 shadow-md sticky top-0 z-50">
      <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
        {/* Logo / Brand */}
        <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
          RAG AI
        </div>

        {/* Theme Toggle Button */}
        <ThemeToggle />
      </div>
    </nav>
  );
};

export default Navbar;
