'use client';

import { useState, useRef, useEffect } from 'react';
import ResearchStream from './ResearchStream';
import QuestionInput from './QuestionInput';

export default function PaperResearch() {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [researchId, setResearchId] = useState<string | null>(null);
  const [streamData, setStreamData] = useState<Array<{type: string, content: string}>>([]);
  const [error, setError] = useState('');
  const streamEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new data arrives
  useEffect(() => {
    if (streamEndRef.current) {
      streamEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamData]);

  const validateUrl = (url: string): boolean => {
    // Basic validation for arXiv URLs
    return url.trim() !== '' && (
      url.includes('arxiv.org/abs/') || 
      url.endsWith('.pdf') || 
      url.includes('pdf')
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateUrl(url)) {
      setError('Please enter a valid arXiv URL or PDF link');
      return;
    }
    
    setError('');
    setIsLoading(true);
    setStreamData([]);
    
    try {
      // Start research session
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/research/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to start research');
      }
      
      const data = await response.json();
      setResearchId(data.researchId);
      
      // Connect to SSE endpoint to stream research progress
      const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/research/stream?id=${data.researchId}`);
      
      eventSource.onmessage = (event) => {
        const eventData = JSON.parse(event.data);
        
        if (eventData.type === 'complete') {
          eventSource.close();
          setIsLoading(false);
        } else {
          setStreamData(prev => [...prev, eventData]);
        }
      };
      
      eventSource.onerror = () => {
        eventSource.close();
        setIsLoading(false);
      };
      
    } catch (error) {
      console.error('Research error:', error);
      setError('Failed to process the paper. Please try again.');
      setIsLoading(false);
    }
  };

  const handleAskQuestion = async (question: string) => {
    if (!researchId) return;
    
    // Add user question to stream
    setStreamData(prev => [...prev, { type: 'user-question', content: question }]);
    
    try {
      const response = await fetch('/api/research/question', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          researchId, 
          question 
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to process question');
      }
      
      const answerData = await response.json();
      setStreamData(prev => [...prev, { 
        type: 'agent-answer', 
        content: answerData.answer 
      }]);
      
    } catch (error) {
      console.error('Question error:', error);
      setStreamData(prev => [...prev, { 
        type: 'error', 
        content: 'Failed to answer question. Please try again.' 
      }]);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6 text-center">Deep Paper</h1>
      
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter arXiv URL (e.g., https://arxiv.org/abs/2307.09288) or PDF link"
            className="flex-grow px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className={`px-6 py-2 rounded font-medium ${
              isLoading 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            {isLoading ? 'Researching...' : 'Research'}
          </button>
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
      </form>
      
      <div className="mb-6">
        <QuestionInput 
          onSubmit={handleAskQuestion} 
          disabled={!researchId || isLoading} 
        />
      </div>
      
      {(streamData.length > 0 || isLoading) && (
        <div className="border rounded-lg bg-gray-50 p-4">
          <h2 className="text-xl font-semibold mb-4">Research Progress</h2>
          
          <ResearchStream data={streamData} />
          
          {isLoading && (
            <div className="flex items-center justify-center py-4">
              <div className="animate-pulse flex space-x-2">
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
              </div>
            </div>
          )}
          
          <div ref={streamEndRef} />
        </div>
      )}
    </div>
  );
}
