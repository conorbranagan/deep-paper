'use client';

import React, { useState, useRef, useEffect } from 'react';
import ResearchStream from './ResearchStream';
import { Search } from 'lucide-react';



export default function ExploreView() {
  const [query, setQuery] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [isResearching, setIsResearching] = useState<boolean>(false);
  const [submittedQuery, setSubmittedQuery] = useState<string>('');
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
      setIsResearching(false);
      return;
    }
    setHasSearched(true);
    setIsResearching(true);
    setSubmittedQuery(query);
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
              disabled={isResearching}
            />
            <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
              <Search className={`h-5 w-5 ${isResearching ? 'text-gray-400' : 'text-gray-600'}`} />
            </div>
          </div>
          {error && <p className="text-red-500 mt-2 text-center">{error}</p>}
        </form>
      </div>

      {hasSearched && (
        <ResearchStream
          sourceURL={`${process.env.NEXT_PUBLIC_API_URL}/api/research/explore`}
          queryParams={{ query: submittedQuery, model: "openai/gpt-4o-mini" }}
          onComplete={() => setIsResearching(false)}
        />
      )}
    </div>
  );
};
