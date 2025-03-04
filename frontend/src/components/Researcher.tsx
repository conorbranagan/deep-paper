'use client';

import { useState, useRef, useEffect } from 'react';
import QuestionInput from './QuestionInput';
import TopicList from './TopicList';
import TopicDetail from './TopicDetail';
import ResearchStream from './ResearchStream';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import MarkdownRenderer from './ui/markdown';

interface Topic {
  topic: string;
  summary: string;
  further_reading: Array<{
    title: string;
    author: string;
    year: number;
    url: string;
  }>;
}

interface PaperData {
  abstract: string;
  summary: string;
  topics: Topic[];
}

interface ResearchStreamData {
  type: string;
  content: string;
}

export default function Researcher() {
  const [url, setUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [paperData, setPaperData] = useState<PaperData | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [error, setError] = useState<string>('');
  const [showAbstract, setShowAbstract] = useState<boolean>(false);
  const paperContentRef = useRef<HTMLDivElement>(null);

  // New states for research question functionality
  const [isResearching, setIsResearching] = useState<boolean>(false);
  const [researchStream, setResearchStream] = useState<ResearchStreamData[]>([]);

  // Scroll to paper content when loaded
  useEffect(() => {
    if (paperData && paperContentRef.current) {
      paperContentRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [paperData]);

  const validateUrl = (url: string): boolean => {
    return url.startsWith('https://arxiv.org/abs')
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateUrl(url)) {
      setError('Please enter a valid arXiv URL (e.g. https://arxiv.org/abs/2005.14165)');
      return;
    }

    setError('');
    setIsLoading(true);
    setPaperData(null);
    setSelectedTopic(null);
    setShowAbstract(false);
    setResearchStream([]);

    try {
      // Call summarize endpoint
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/research/summarize?url=${encodeURIComponent(url)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error('Failed to summarize paper');
      }

      const data = await response.json();
      setPaperData(data);
      setIsLoading(false);
    } catch (error) {
      console.error('Research error:', error);
      setError('Failed to process the paper. Please try again.');
      setIsLoading(false);
    }
  };

  const handleTopicSelect = (topic: Topic) => {
    setSelectedTopic(topic);
  };

  const resetTopicSelection = () => {
    setSelectedTopic(null);
  };

  const toggleAbstract = () => {
    setShowAbstract(!showAbstract);
  };

  // New function to handle research question submission
  const handleQuestionSubmit = async (questionText: string) => {
    if (!url || !questionText.trim()) {
      setError('Please enter both a valid URL and a research question');
      return;
    }

    setError('');
    setIsResearching(true);
    setResearchStream([]);

    try {
      const deepURL = `${process.env.NEXT_PUBLIC_API_URL}/api/research/deep?url=${encodeURIComponent(url)}&question=${encodeURIComponent(questionText)}`
      const eventSource = new EventSource(deepURL);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'complete') {
            eventSource.close();
            setIsResearching(false);
          } else if (data.type === 'error') {
            throw new Error(data.content || 'An error occurred');
          } else {
            setResearchStream(prev => [...prev, data]);
          }
        } catch (error) {
          console.error('Error parsing stream data:', error);
          setError('Failed to research');
          eventSource.close();
          setIsResearching(false);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setIsResearching(false);
      };
    } catch (error) {
      console.error('Deep research error:', error);
      setResearchStream(prev => [
        ...prev,
        {
          type: 'error',
          content: 'Failed to process your research question. Please try again.'
        }
      ]);
      setIsResearching(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6 text-center">Paper Research Assistant</h1>

      <form onSubmit={handleSubmit} className="mb-8">
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter arXiv URL (e.g., https://arxiv.org/abs/2307.09288)"
            className="flex-grow px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className={`px-6 py-2 rounded font-medium ${isLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
          >
            {isLoading ? 'Processing...' : 'Research'}
          </button>
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
      </form>

      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-pulse flex space-x-2">
            <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
            <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
            <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
          </div>
          <div className="ml-4">Analyzing paper...</div>
        </div>
      )}

      {paperData && !isLoading && (
        <div className="space-y-6" ref={paperContentRef}>
          {/* Paper Overview */}
          <h2 className="text-2xl font-bold mb-4">📝 Overview</h2>
          <Card>
            <CardContent className="pt-6">
              <h2 className="text-2xl font-bold mb-4">Summary</h2>
              <MarkdownRenderer>
                {paperData.summary}
              </MarkdownRenderer>

              <div className="mt-6 ">
                <div
                  onClick={toggleAbstract}
                  className="p-3 cursor-pointer hover:bg-gray-50"
                >
                  <span className="text-md text-gray-500 align-text-middle">
                    {showAbstract ? '▼' : '▶'}
                  </span>
                  <span className="text-xl font-bold p-2">Abstract</span>
                </div>

                {showAbstract && (
                  <div className="p-4 border-t border-gray-200">
                    <p className="text-gray-700">{paperData.abstract}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Topic Navigation */}
          {!selectedTopic ? (
            <div>
              <h2 className="text-2xl font-bold mb-4">🔍 Explore Key Topics</h2>
              <TopicList topics={paperData.topics} onTopicSelect={handleTopicSelect} />
            </div>
          ) : (
            <div>
              <div className="flex items-center mb-4">
                <Button
                  variant="outline"
                  onClick={resetTopicSelection}
                  className="mr-4"
                >
                  ← Back to Topics
                </Button>
                <h2 className="text-2xl font-bold">{selectedTopic.topic}</h2>
              </div>
              <TopicDetail topic={selectedTopic} paperUrl={url} />
            </div>
          )}


          {/* Question Input - now connected to handleQuestionSubmit */}
          <h2 className="text-2xl font-bold mb-4">❓ Research Further</h2>
          <div className="mb-6">
            <QuestionInput
              onSubmit={handleQuestionSubmit}
              disabled={!paperData || isLoading || isResearching}
              placeholder="Ask a research question about this paper..."
            />
            {researchStream.length > 0 && (
              <Card className="mt-6">
                <CardContent className="pt-6">
                  <ResearchStream data={researchStream} />
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
                <div className="ml-3 text-sm text-gray-600">Researching your question...</div>
              </div>
            )}

          </div>

        </div>
      )}
    </div>
  );
}