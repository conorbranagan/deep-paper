"use client";

import React from "react";
import { Card, CardContent } from "./ui/card";
import ResearchStreamItem from "./ResearchStreamItem";
import { useEventSource } from "./utils/EventSourceManager";

interface ResearchStreamData {
  type: string;
  content: string;
}

type QueryParams = {
  [key: string]: string | string[];
};

interface ResearchStreamProps {
  sourceURL: string;
  queryParams: QueryParams;
  onComplete?: () => void;
}

const getContentStyle = (type: string) => {
  switch (type) {
    case "thought":
      return "bg-purple-50 border-purple-200 text-purple-800";
    case "action":
      return "bg-yellow-50 border-yellow-200 text-yellow-800";
    case "result":
      return "bg-green-50 border-green-200 text-green-800";
    case "summary":
      return "bg-blue-50 border-blue-200 text-blue-800";
    case "error":
      return "bg-red-50 border-red-200 text-red-800";
    case "user-question":
      return "bg-gray-100 border-gray-300 text-gray-800";
    case "agent-answer":
      return "bg-blue-50 border-blue-200 text-blue-800";
    default:
      return "bg-gray-50 border-gray-200 text-gray-800";
  }
};

export default function ResearchStream({
  sourceURL,
  queryParams,
  onComplete,
}: ResearchStreamProps) {
  const { messages, status } = useEventSource<ResearchStreamData>({
    url: sourceURL,
    queryParams,
    onComplete,
  });

  const isResearching = status === "connecting" || status === "streaming";

  return (
    <>
      {messages.length > 0 && (
        <Card className="mt-6">
          <CardContent className="pt-6">
            {messages.map((item, index) => (
              <div
                key={index}
                className={`border rounded-md p-4 mb-4 ${getContentStyle(item.type)}`}
              >
                <ResearchStreamItem
                  key={index}
                  type={item.type}
                  content={item.content}
                />
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      {isResearching && (
        <div className="mt-3 flex items-center">
          <div className="animate-pulse flex space-x-2">
            <div className="h-2 w-2 bg-blue-600 rounded-full"></div>
            <div className="h-2 w-2 bg-blue-600 rounded-full"></div>
            <div className="h-2 w-2 bg-blue-600 rounded-full"></div>
          </div>
          <div className="ml-3 text-sm text-gray-600">Researching...</div>
        </div>
      )}
    </>
  );
}
