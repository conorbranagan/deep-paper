"use client";

import React, { useState, useRef, useEffect } from "react";
import { Search, ExternalLink, BookOpen } from "lucide-react";
import { makeAPIURL } from "./lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";
import MarkdownRenderer from "./ui/markdown";
import { useEventSource } from "./utils/EventSourceManager";

// Must match the python regex in backend/app/agents/explore.py
const CITATION_REGEX =
  /(citation_id:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/g;

interface Citation {
  id: string;
  title: string;
  arxiv_id: string;
}

interface ExploreContentMessage {
  type: string;
  content: string;
  payload?: Citation;
}

interface ExploreViewProps {
  onResearchPaper: (url: string) => void;
  selectedModel: string;
}

export default function ExploreView({
  onResearchPaper,
  selectedModel,
}: ExploreViewProps) {
  const [query, setQuery] = useState<string>("");
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [submittedQuery, setSubmittedQuery] = useState<string>("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus the input when component mounts
    if (inputRef.current && !hasSearched) {
      inputRef.current.focus();
    }
  }, [hasSearched]);

  const { messages, status, error } = useEventSource<ExploreContentMessage>({
    url: makeAPIURL("api/explore"),
    queryParams: {
      query: submittedQuery,
      model: selectedModel,
    },
    enabled: submittedQuery.length > 0,
  });
  const isLoading = status === "connecting" || status === "streaming";

  const exploreData = messages
    .filter((msg) => msg.type === "content")
    .map((msg) => msg.content)
    .join("");
  const citationsMap = messages
    .filter((msg) => msg.type === "citation")
    .reduce((acc: Record<string, Citation>, msg: ExploreContentMessage) => {
      if (msg.payload) {
        acc[msg.payload.id] = msg.payload;
      }
      return acc;
    }, {});

  return (
    <div
      className={`max-w-5xl mx-auto px-4 py-8 ${!hasSearched ? "flex flex-col justify-center min-h-[70vh]" : ""}`}
    >
      <div
        className={`transition-all duration-300 ${hasSearched ? "mb-8" : "mb-0"}`}
      >
        {!hasSearched && (
          <h1 className="font-bold text-center text-4xl mb-8">Explore</h1>
        )}

        <form
          onSubmit={async (e: React.FormEvent) => {
            e.preventDefault();
            if (!query.trim()) {
              return;
            }
            setHasSearched(true);
            setSubmittedQuery(query);
          }}
          className="max-w-2xl mx-auto"
        >
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question or enter a topic of interest..."
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
        </form>
      </div>
      {!hasSearched && (
        <div className="mt-8">
          <p className="text-gray-500 text-center">
            Explore a topic across a corpus of academic papers.
          </p>
        </div>
      )}

      {hasSearched && (
        <div className="mt-8">
          {exploreData ? (
            <div className="prose max-w-none">
              <div className="response-container">
                <MarkdownRenderer
                  /* FIXME: This doesn't work for non-p types (e.g. bullets). Need children to get rendered with their types */
                  additionalComponents={{
                    p: ({ children }) => {
                      // Intersperses citations with links to the citations
                      const text = String(children);
                      const parts = text.split(CITATION_REGEX);

                      if (parts.length <= 1) {
                        return <div className="mt-5">{children}</div>;
                      }

                      return (
                        <div className="mt-5">
                          {parts.map((part, idx) => {
                            const sp = part.split("citation_id:");
                            if (sp.length > 1 && citationsMap[sp[1]]) {
                              const citationId = sp[1];
                              const citation = citationsMap[citationId];
                              return (
                                <React.Fragment key={idx}>
                                  <CitationLink
                                    citation={citation}
                                    handleResearchPaper={(arxivId) =>
                                      onResearchPaper(
                                        `https://arxiv.org/abs/${arxivId}`
                                      )
                                    }
                                  />
                                </React.Fragment>
                              );
                            }
                            return (
                              <React.Fragment key={idx}>{part}</React.Fragment>
                            );
                          })}
                        </div>
                      );
                    },
                  }}
                >
                  {exploreData}
                </MarkdownRenderer>
              </div>
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-pulse flex space-x-2">
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
              </div>
              <div className="ml-4">Researching...</div>
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

function CitationLink({
  citation,
  handleResearchPaper,
}: {
  citation: Citation;
  handleResearchPaper: (arxivId: string) => void;
}) {
  return (
    <TooltipProvider>
      <Tooltip delayDuration={100}>
        <TooltipTrigger asChild>
          <span className="citation-id cursor-pointer text-blue-600 font-medium">
            {citation.arxiv_id}
          </span>
        </TooltipTrigger>
        <TooltipContent className="p-3 max-w-md bg-white shadow-lg rounded-lg border">
          <div className="space-y-2">
            <span className="font-medium">{citation.title}</span>
            <div className="flex space-x-2 mt-1">
              <a
                href={`https://arxiv.org/abs/${citation.arxiv_id}`}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => {
                  e.preventDefault();
                  handleResearchPaper(citation.arxiv_id);
                }}
                className="text-blue-600 hover:text-blue-800 flex items-center"
                title="Research this paper"
              >
                <BookOpen className="h-4 w-4 mr-1" />
                <span>Research</span>
              </a>
              <a
                href={`https://arxiv.org/abs/${citation.arxiv_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 flex items-center"
              >
                <ExternalLink className="h-4 w-4 mr-1" />
                <span>View</span>
              </a>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
