'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Search, ExternalLink, BookOpen } from 'lucide-react';
import { makeAPIURL } from './lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import MarkdownRenderer from './ui/markdown';
interface Citation {
  title: string;
  arxiv_id: string;
}

interface ExploreResponse {
  response: string;
  citations: Record<string, Citation>;
}

export default function ExploreView() {
  const [query, setQuery] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [, setSubmittedQuery] = useState<string>('');
  const [exploreData, setExploreData] = useState<ExploreResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus the input when component mounts
    if (inputRef.current && !hasSearched) {
      inputRef.current.focus();
    }
  }, [hasSearched]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setError('Please enter a research topic');
      return;
    }

    setHasSearched(true);
    setIsLoading(true);
    setSubmittedQuery(query);
    setExploreData(null);

    try {
      const response = await fetch(makeAPIURL(`api/explore?query=${encodeURIComponent(query)}&model=openai/gpt-4o-mini`));

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const data = await response.json();
      setExploreData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }

  const handleResearchPaper = (arxivId: string) => {
    // Implement the research paper functionality
    console.log(`Researching paper: ${arxivId}`);
    // You would typically navigate to a research view or trigger another action
  }

  return (
    <div className={`max-w-5xl mx-auto px-4 py-8 ${!hasSearched ? 'flex flex-col justify-center min-h-[70vh]' : ''}`}>
      <div className={`transition-all duration-300 ${hasSearched ? 'mb-8' : 'mb-0'}`}>
        {!hasSearched && (
          <>
            <h1 className="font-bold text-center text-4xl mb-3">
              Explore
            </h1>
          </>
        )}

        <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
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
              <Search className={`h-5 w-5 ${isLoading ? 'text-gray-400' : 'text-gray-600'}`} />
            </div>
          </div>
          {error && <p className="text-red-500 mt-2 text-center">{error}</p>}
        </form>
      </div>

      {hasSearched && (
        <div className="mt-8">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-pulse flex space-x-2">
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
              </div>
              <div className="ml-4">Researching...</div>
            </div>
          ) : exploreData ? (
            <div className="prose max-w-none">
              <div className="response-container">
                <MarkdownRenderer
                  additionalComponents={{
                    p: ({ children }) => {
                      // Intersperses citations with links to the citations
                      const text = String(children);
                      const parts = text.split(/(\(\d+\.\d+\))/g);
                      
                      if (parts.length <= 1) {
                        return <div>{children}</div>;
                      }
                      
                      return (
                        <div className="mt-5">
                          {parts.map((part, idx) => {
                            const match = part.match(/\((\d+\.\d+)\)/);
                            if (match && exploreData.citations[match[1]]) {
                              const citationId = match[1];
                              const citation = exploreData.citations[citationId];
                              return (
                                <React.Fragment key={idx}>
                                  <CitationLink 
                                    citation={citation} 
                                    handleResearchPaper={handleResearchPaper} 
                                  />
                                </React.Fragment>
                              );
                            }
                            return <React.Fragment key={idx}>{part}</React.Fragment>;
                          })}
                        </div>
                      );
                    }
                  }}
                >{exploreData.response}</MarkdownRenderer>
              </div>
            </div>
          ) : (
            <p className="text-center text-gray-500">No results found. Try another query.</p>
          )}
        </div>
      )}
    </div>
  );
};

function CitationLink({ citation, handleResearchPaper }: { citation: Citation, handleResearchPaper: (arxivId: string) => void }) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="citation-id cursor-pointer text-blue-600 font-medium">
            ({citation.arxiv_id})
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