'use client';

import { useState, useRef, useEffect } from 'react';
import QuestionInput from './QuestionInput';
import TopicList from './TopicList';
import TopicDetail from './TopicDetail';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import ReactMarkdown from 'react-markdown';

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

export default function Researcher() {
  const [url, setUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [paperData, setPaperData] = useState<PaperData | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [error, setError] = useState<string>('');
  const paperContentRef = useRef<HTMLDivElement>(null);

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

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6 text-center">Deep Paper</h1>

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

      {/* Question Input - could be used later for asking questions about the paper */}
      <div className="mb-6">
        <QuestionInput
          onSubmit={() => { }}
          disabled={!paperData || isLoading}
          placeholder="Ask a question about this paper"
        />
      </div>

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
          <Card>
            <CardContent className="pt-6">
              <h2 className="text-2xl font-bold mb-4">Abstract</h2>
              <p className="text-gray-700 mb-4">{paperData.abstract}</p>

              <h2 className="text-2xl font-bold mb-4">Summary</h2>
              <ReactMarkdown components={{ ul: ({ ...props }) => (<ul style={{ display: "block", listStyleType: "disc", paddingInlineStart: "40px", }} {...props} />), ol: ({ ...props }) => (<ul style={{ display: "block", listStyleType: "decimal", paddingInlineStart: "40px", }} {...props} />), }}>
                {paperData.summary}
              </ReactMarkdown>
            </CardContent>
          </Card>

          {/* Topic Navigation */}
          {!selectedTopic ? (
            <div>
              <h2 className="text-2xl font-bold mb-4">🔍 Explore Further</h2>
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

          {/* Future Feature Areas - Stubbed UI */}
          <Tabs defaultValue="current" className="mt-8">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="current">Current Paper</TabsTrigger>
              <TabsTrigger value="related">Related Papers</TabsTrigger>
              <TabsTrigger value="explore">Deep Exploration</TabsTrigger>
              <TabsTrigger value="saved">Saved Items</TabsTrigger>
            </TabsList>

            <TabsContent value="current" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <h3 className="text-xl font-semibold mb-3">Full Paper Content</h3>
                  <p className="text-gray-500">Full paper contents will be available here.</p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="related" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <h3 className="text-xl font-semibold mb-3">Related Papers</h3>
                  <p className="text-gray-500">Related papers for the current topic will be displayed here.</p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="explore" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <h3 className="text-xl font-semibold mb-3">Topic Deep Dive</h3>
                  <p className="text-gray-500">Explore the current paper in depth with a focus on the selected topic.</p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="saved" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <h3 className="text-xl font-semibold mb-3">Saved Highlights</h3>
                  <p className="text-gray-500">Your saved highlights and papers will appear here.</p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
}