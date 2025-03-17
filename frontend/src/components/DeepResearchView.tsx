"use client";

import React, { useState, useRef, useEffect } from "react";
import { Search } from "lucide-react";
import Image from "next/image";
import { makeAPIURL } from "./lib/utils";
import MarkdownRenderer from "./ui/markdown";
import { useEventSource } from "./utils/EventSourceManager";

type ResearchStatusMessage = {
  type: "status";
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

// Add a type for browser options
type BrowserType = "text_browser" | "browser_use" | "browser_use_headless";

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
  const [browserType, setBrowserType] = useState<BrowserType>("text_browser");
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
      mode: browserType,
    },
    enabled: submittedURL.length > 0,
  });
  const isLoading = status === "connecting" || status === "streaming";

  let content = messages
    .filter((msg) => msg.type === "content")
    .map((msg) => msg.content)
    .join("");

  // Sometimes the content is wrapped in code braces, I don't know why. Let's remove them.
  if (content.startsWith("```\n") && content.endsWith("\n```")) {
    content = content.slice(4, -3);
  }

  const sources = messages.filter((msg) => msg.type === "source");
  const lastStatus = messages
    .filter((msg) => msg.type === "status")
    .pop() as ResearchStatusMessage;

  // Add state for tracking expanded sources view
  const [showAllSources, setShowAllSources] = useState<boolean>(false);

  return (
    <div
      className={`max-w-5xl mx-auto px-4 py-8 ${!hasSearched ? "flex flex-col justify-center min-h-[70vh]" : ""}`}
    >
      <div
        className={`transition-all duration-300 ${hasSearched ? "mb-8" : "mb-0"}`}
      >
        {!hasSearched && (
          <h1 className="font-bold text-center text-4xl mb-3">
            Research a Paper
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
          <div className="flex gap-2 items-center">
            <div className="relative flex-grow">
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

            <select
              value={browserType}
              onChange={(e) => setBrowserType(e.target.value as BrowserType)}
              className="w-50 px-2 py-4 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              disabled={isLoading}
              aria-label="Browser Type"
            >
              <option value="text_browser">Text Browser</option>
              <option value="browser_use">Browser Use</option>
              <option value="browser_use_headless">
                Browser Use (Headless)
              </option>
            </select>
          </div>

          {error && <p className="text-red-500 mt-2 text-center">{error}</p>}
          {streamError && (
            <p className="text-red-500 mt-2 text-center">{streamError}</p>
          )}
        </form>
      </div>
      {!hasSearched && (
        <div className="mt-8">
          <p className="text-gray-500 text-center">
            Analyze a paper and comb the web for related resources to generate a
            research report.
          </p>
        </div>
      )}

      {hasSearched && (
        <div className="mt-8">
          {/* Sources Section */}
          {sources.length > 0 && (
            <div className="mb-6 border rounded-lg p-4 bg-gray-50">
              <div
                onClick={() => setShowAllSources(!showAllSources)}
                className="flex justify-between items-center mb-3 cursor-pointer hover:bg-gray-100 p-2 rounded-md transition-colors"
              >
                <h3 className="text-lg font-semibold">
                  {`${sources.length}`}{" "}
                  {sources.length === 1 ? "Source" : "Sources"}
                </h3>
                <span className="text-sm text-blue-600">
                  {showAllSources ? "Collapse" : "Expand"}
                </span>
              </div>

              {/* Collapsed view - Icons only */}
              {!showAllSources && (
                <div className="flex flex-wrap gap-3 justify-start">
                  {sources.map((source, index) => (
                    <a
                      key={index}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={source.title}
                      className="flex items-center p-2 border rounded-lg bg-white hover:bg-gray-100 transition-colors w-[170px]"
                    >
                      {source.favicon ? (
                        <Image
                          src={source.favicon}
                          alt={source.title}
                          width={24}
                          height={24}
                          className="w-6 h-6 object-contain"
                        />
                      ) : (
                        <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center text-xs">
                          {source.title.charAt(0)}
                        </div>
                      )}
                      <span className="ml-2 text-sm font-medium truncate max-w-[150px]">
                        {source.title}
                      </span>
                    </a>
                  ))}
                </div>
              )}

              {/* Expanded view - Full details */}
              {showAllSources && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {sources.map((source, index) => (
                    <div key={index} className="p-3 border rounded bg-white">
                      <div className="flex items-center gap-3 mb-2">
                        {source.favicon && (
                          <Image
                            src={source.favicon}
                            alt="Site favicon"
                            width={20}
                            height={20}
                            className="w-5 h-5 object-contain"
                          />
                        )}
                        <p className="font-medium text-sm">{source.title}</p>
                      </div>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:underline block mb-2 truncate"
                      >
                        {source.url}
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Main Content Section */}
          <div>
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
                  {lastStatus ? lastStatus.message : "Loading..."}
                </div>
              </div>
            ) : (
              <p className="text-center text-gray-500">
                No results found. Try another query.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
