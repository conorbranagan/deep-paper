"use client";

import React from "react";
import MarkdownRenderer from "./ui/markdown";

export default function ResearchStreamItem({
  type,
  content,
}: {
  type: string;
  content: string;
}) {
  const getTypeDetails = (type: string) => {
    switch (type) {
      case "thought":
        return {
          icon: "💭",
          label: "Thinking",
        };
      case "action":
        return {
          icon: "⚙️",
          label: "Action",
        };
      case "result":
        return {
          icon: "📊",
          label: "Result",
        };
      case "summary":
        return {
          icon: "📝",
          label: "Summary",
        };
      case "error":
        return {
          icon: "❌",
          label: "Error",
        };
      case "user-question":
        return {
          icon: "❓",
          label: "Your Question",
        };
      case "agent-answer":
        return {
          icon: "🤖",
          label: "Answer",
        };
      default:
        return {
          icon: "ℹ️",
          label: "Info",
        };
    }
  };

  const { icon, label } = getTypeDetails(type);

  return (
    <div className="space-y-4">
      <div className="flex items-center mb-2">
        <span className="mr-2">{icon}</span>
        <span className="font-medium">{label}</span>
      </div>
      <div className="prose max-w-none">
        <MarkdownRenderer
          containerStyle={{
            overflow: "scroll",
          }}
        >
          {content}
        </MarkdownRenderer>
      </div>
    </div>
  );
}
