'use client';

import { useState, useRef, useEffect } from 'react';
import QuestionInput from './QuestionInput';
import TopicList from './TopicList';
import TopicDetail from './TopicDetail';
import ResearchStream from './ResearchStream';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import MarkdownRenderer from './ui/markdown';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

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

interface PaperSummary {
  title: string;
  abstract: string;
  summary: string;
  topics: Topic[];
}

interface ResearchStreamData {
  type: string;
  content: string;
}

interface ModelOption {
  id: string;
  name: string;
}

// Model configuration
const modelOptions: ModelOption[] = [
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'anthropic/claude-3-7-sonnet-latest', name: 'Claude 3.7 Sonnet' },
  { id: 'openai/gpt-4o', name: 'GPT-4o' },
];

export default function Researcher() {
  const [url, setUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [paperSummary, setPaperSummary] = useState<PaperSummary | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [error, setError] = useState<string>('');
  const [showAbstract, setShowAbstract] = useState<boolean>(false);
  const paperContentRef = useRef<HTMLDivElement>(null);
  const [selectedModel, setSelectedModel] = useState<string>(modelOptions[0].id);

  // New states for research question functionality
  const [isResearching, setIsResearching] = useState<boolean>(false);
  const [researchStream, setResearchStream] = useState<ResearchStreamData[]>([]);

  // Scroll to paper content when loaded
  useEffect(() => {
    if (paperSummary && paperContentRef.current) {
      paperContentRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [paperSummary]);

  const validateUrl = (url: string): boolean => {
    return url.startsWith('https://arxiv.org/abs')
  };
  
  // Helper function for API calls
  const callApi = async (endpoint: string, params: Record<string, string>) => {
    // Add model to params
    const allParams = { ...params, model: selectedModel };
    
    // Convert params to URL search params
    const searchParams = new URLSearchParams();
    Object.entries(allParams).forEach(([key, value]) => {
      searchParams.append(key, value);
    });
    
    const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/${endpoint}?${searchParams.toString()}`;
    
    return fetch(apiUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateUrl(url)) {
      setError('Please enter a valid arXiv URL (e.g. https://arxiv.org/abs/2005.14165)');
      return;
    }

    setError('');
    setIsLoading(true);
    setPaperSummary(null);
    setSelectedTopic(null);
    setShowAbstract(false);
    setResearchStream([]);

    try {
      // Call summarize endpoint using helper function
      const response = await callApi('research/summarize', { url });

      if (!response.ok) {
        throw new Error('Failed to summarize paper');
      }

      const data = await response.json();
      setPaperSummary(data);
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
      // Using search params to properly encode URL parameters including the model
      const searchParams = new URLSearchParams({
        url: url,
        question: questionText,
        model: selectedModel
      });
      
      const deepURL = `${process.env.NEXT_PUBLIC_API_URL}/api/research/deep?${searchParams.toString()}`;
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
          <Select
            value={selectedModel}
            onValueChange={setSelectedModel}
            disabled={isLoading}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {modelOptions.map((model) => (
                <SelectItem key={model.id} value={model.id}>
                  {model.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            type="submit"
            disabled={isLoading}
            className={`px-6 py-2 rounded font-medium ${isLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
          >
            {isLoading ? 'Processing...' : 'Research'}
          </Button>
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
          <div className="ml-4">Analyzing paper with {modelOptions.find(m => m.id === selectedModel)?.name}...</div>
        </div>
      )}

      {paperSummary && !isLoading && (
        <div className="space-y-6" ref={paperContentRef}>
          {/* Paper Overview */}
          <h2 className="text-2xl font-bold mb-4">📝 Overview</h2>
          <Card>
            <CardContent className="pt-6">
              <h2 className="text-3xl font-bold mb-4">{paperSummary.title}</h2>
              <h3 className="text-xl font-bold mb-4">Summary</h3>
              <MarkdownRenderer>
                {paperSummary.summary}
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
                    <p className="text-gray-700">{paperSummary.abstract}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Topic Navigation */}
          {!selectedTopic ? (
            <div>
              <h2 className="text-2xl font-bold mb-4">🔍 Explore Key Topics</h2>
              <TopicList topics={paperSummary.topics} onTopicSelect={handleTopicSelect} />
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
              <TopicDetail topic={selectedTopic} paperUrl={url} model={selectedModel} />
            </div>
          )}


          {/* Question Input - now connected to handleQuestionSubmit */}
          <h2 className="text-2xl font-bold mb-4">❓ Research Further</h2>
          <div className="mb-6">
            <QuestionInput
              onSubmit={handleQuestionSubmit}
              disabled={!paperSummary || isLoading || isResearching}
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
                <div className="ml-3 text-sm text-gray-600">Researching your question with {modelOptions.find(m => m.id === selectedModel)?.name}...</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}