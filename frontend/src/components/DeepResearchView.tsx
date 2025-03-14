"use client";

import React, { useState, useRef, useEffect } from "react";
import { Search } from "lucide-react";
import Image from "next/image";
import { makeAPIURL } from "./lib/utils";
import MarkdownRenderer from "./ui/markdown";
import { useEventSource } from "./utils/EventSourceManager";

type ResearchStatus = "starting" | "browsing" | "analyzing" | "done";

type ResearchStatusMessage = {
  type: "status";
  status: ResearchStatus;
  message: string;
};

type ResearchSourceMessage = {
  type: "source";
  url: string;
  title: string;
  favicon: string;
  summary?: string;
};

type ResearchContentMessage = {
  type: "content";
  content: string;
};

type ResearchError = {
  type: "error";
  error: string;
};

type ResearchMessage =
  | ResearchStatusMessage
  | ResearchSourceMessage
  | ResearchContentMessage
  | ResearchError;

interface DeepResearchViewProps {
  selectedModel: string;
}

function isValidArxivUrl(url: string): boolean {
  return url.startsWith("https://arxiv.org/abs/");
}

export default function DeepResearchView({
  selectedModel,
}: DeepResearchViewProps) {
  const [url, setURL] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [submittedURL, setSubmittedURL] = useState<string>("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus the input when component mounts
    if (inputRef.current && !hasSearched) {
      inputRef.current.focus();
    }
  }, [hasSearched]);

  const {
    messages,
    status,
    error: streamError,
  } = useEventSource<ResearchMessage>({
    url: makeAPIURL("api/paper/deep-research"),
    queryParams: {
      url: submittedURL,
      model: selectedModel,
    },
    enabled: submittedURL.length > 0,
  });
  const isLoading = status === "connecting" || status === "streaming";

  const content = messages
    .filter((msg) => msg.type === "content")
    .map((msg) => msg.content)
    .join("");

  const sources = messages.filter((msg) => msg.type === "source");

  const lastStatus = messages
    .filter((msg) => msg.type === "status")
    .pop() as ResearchStatusMessage;

  return (
    <div
      className={`max-w-5xl mx-auto px-4 py-8 ${!hasSearched ? "flex flex-col justify-center min-h-[70vh]" : ""}`}
    >
      <div
        className={`transition-all duration-300 ${hasSearched ? "mb-8" : "mb-0"}`}
      >
        {!hasSearched && (
          <h1 className="font-bold text-center text-4xl mb-3">
            Deep Research a Paper
          </h1>
        )}

        <form
          onSubmit={async (e: React.FormEvent) => {
            e.preventDefault();
            if (!url.trim()) {
              return;
            }
            if (!isValidArxivUrl(url)) {
              setError(
                "Please enter a valid ArXiv paper URL (for example: https://arxiv.org/abs/2303.01360)"
              );
              return;
            }
            setError(null);
            setHasSearched(true);
            setSubmittedURL(url);
          }}
          className="max-w-2xl mx-auto"
        >
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={url}
              onChange={(e) => setURL(e.target.value)}
              placeholder="Enter an ArXiv paper URL..."
              className="w-full px-4 py-3 pr-12 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg"
              disabled={isLoading}
            />
            <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
              <Search
                className={`h-5 w-5 ${isLoading ? "text-gray-400" : "text-gray-600"}`}
              />
            </div>
          </div>
          {error && <p className="text-red-500 mt-2 text-center">{error}</p>}
          {streamError && (
            <p className="text-red-500 mt-2 text-center">{streamError}</p>
          )}
        </form>
      </div>

      {hasSearched && (
        <div className="mt-8">
          {/* Sources Section */}
          {sources.length > 0 && (
            <div className="mb-6 border rounded-lg p-4 bg-gray-50">
              <h3 className="text-lg font-semibold mb-3">Sources</h3>
              <div className="space-y-3">
                {sources.map((source, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-3 p-2 border rounded bg-white"
                  >
                    {source.favicon && (
                      <Image
                        src={source.favicon}
                        alt="Site favicon"
                        width={20}
                        height={20}
                        className="w-5 h-5 object-contain"
                      />
                    )}
                    <div className="flex-1 overflow-hidden">
                      <p className="font-medium text-sm">{source.title}</p>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline truncate block"
                      >
                        {source.url}
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {content ? (
            <div className="prose max-w-none">
              <div className="response-container">
                <MarkdownRenderer>{content}</MarkdownRenderer>
              </div>
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-pulse flex space-x-2">
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
              </div>
              <div className="ml-4">
                {lastStatus ? lastStatus.message : "Initializing..."}
              </div>
            </div>
          ) : (
            <p className="text-center text-gray-500">
              No results found. Try another query.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
