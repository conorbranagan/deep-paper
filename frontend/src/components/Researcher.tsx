'use client';

import { useState, useEffect, useCallback } from 'react';
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
import { Topic } from './types';

interface PaperSummary {
  title: string;
  abstract: string;
  summary: string;
  topics: Topic[];
}

interface ModelOption {
  id: string;
  name: string;
}

interface ResearcherProps {
  onLoadingChange: (tabId: string, isLoading: boolean) => void;
  onTitleChange: (tabId: string, title: string) => void;
  onResearchPaper: (url: string) => void;
  tabId: string;
  initialUrl?: string;
}

const modelOptions: ModelOption[] = [
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini' },
  { id: 'anthropic/claude-3-7-sonnet-latest', name: 'Claude 3.7 Sonnet' },
  { id: 'openai/gpt-4o', name: 'GPT-4o' },
];

const validateUrl = (url: string): boolean => {
  return url.startsWith('https://arxiv.org/abs')
};

export const Researcher: React.FC<ResearcherProps> = ({ onLoadingChange, onTitleChange, onResearchPaper, tabId, initialUrl }: ResearcherProps) => {
  const [url, setUrl] = useState<string>(initialUrl || '');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [paperSummary, setPaperSummary] = useState<PaperSummary | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [error, setError] = useState<string>('');
  const [showAbstract, setShowAbstract] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<string>(modelOptions[0].id);
  const [question, setQuestion] = useState<string>('');

  // Load state from localStorage on initial render
  useEffect(() => {
    try {
      const savedState = localStorage.getItem(`research-state-${tabId}`);
      if (savedState) {
        const parsedState = JSON.parse(savedState);
        setPaperSummary(parsedState.paperSummary);
        setUrl(parsedState.url || '');
        setSelectedModel(parsedState.selectedModel || modelOptions[0].id);
      }
    } catch (error) {
      console.error('Error loading research state from localStorage:', error);
    }
  }, [tabId]);

  // Save state to localStorage whenever paperSummary changes
  useEffect(() => {
    try {
      const stateToSave = {
        paperSummary,
        url,
        selectedModel
      };
      if (paperSummary) {
        localStorage.setItem(`research-state-${tabId}`, JSON.stringify(stateToSave));
      }
    } catch (error) {
      console.error('Error saving research state to localStorage:', error);
    }
  }, [paperSummary, url, selectedModel, tabId]);

  // Changes to loading and title must propagate to container tabs.
  useEffect(() => {
    onLoadingChange?.(tabId, isLoading);
  }, [tabId, isLoading, onLoadingChange]);

  useEffect(() => {
    if (paperSummary?.title) {
      onTitleChange(tabId, paperSummary.title);
    }
  }, [tabId, paperSummary?.title, onTitleChange]);

  const fetchSummary = useCallback(async (url: string, signal: AbortSignal) => {
    if (!validateUrl(url)) {
      setError('Please enter a valid arXiv URL (e.g. https://arxiv.org/abs/2005.14165)');
      return;
    }

    setError('');
    setIsLoading(true);
    setPaperSummary(null);
    setSelectedTopic(null);
    setShowAbstract(false);
    onTitleChange?.(tabId, url);

    try {
      const searchParams = new URLSearchParams();
      searchParams.append('url', url);
      searchParams.append('model', selectedModel);
      const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/research/summarize?${searchParams.toString()}`;

      const fetchPromise = fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: signal,
      });
      const response = await fetchPromise;
      if (!response.ok) {
        throw new Error('Failed to summarize paper');
      }
      const data = await response.json();
      setPaperSummary(data);
      setIsLoading(false);
    } catch (error) {
      if (signal.aborted) {
        return;
      }
      console.error('Research error:', error);
      setError('Failed to process the paper. Please try again.');
      setIsLoading(false);
    }
  }, [selectedModel, onTitleChange, tabId]);

  useEffect(() => {
    const abortController = new AbortController();
    if (initialUrl) {
      fetchSummary(initialUrl, abortController.signal);
    }
    return () => abortController.abort();
  }, [initialUrl, fetchSummary]);


  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6 text-center">Paper Research Assistant</h1>
      <form onSubmit={(e: React.FormEvent) => {
        e.preventDefault();
        const abortController = new AbortController();
        fetchSummary(url, abortController.signal);
      }} className="mb-8">
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
        <div className="space-y-6">
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
                  onClick={() => { setShowAbstract(!showAbstract) }}
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
              <TopicList topics={paperSummary.topics} onTopicSelect={(topic: Topic) => { setSelectedTopic(topic) }} />
            </div>
          ) : (
            <div>
              <div className="flex items-center mb-4">
                <Button
                  variant="outline"
                  onClick={() => { setSelectedTopic(null) }}
                  className="mr-4"
                >
                  ← Back to Topics
                </Button>
                <h2 className="text-2xl font-bold">{selectedTopic.topic}</h2>
              </div>
              <TopicDetail
                topic={selectedTopic}
                paperUrl={url}
                model={selectedModel}
                onResearchPaper={onResearchPaper}
              />
            </div>
          )}

          <h2 className="text-2xl font-bold mb-4">❓ Research Further</h2>
          <div className="mb-6">
            <QuestionInput
              onSubmit={(question: string) => {
                if (!url || !question.trim()) {
                  setError('Please enter both a valid URL and a research question');
                  return;
                }
                setQuestion(question);
                setError('');
              }}
              disabled={!paperSummary || isLoading}
              placeholder="Ask a research question about this paper..."
            />
            <ResearchStream
              url={url}
              model={selectedModel}
              question={question}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default Researcher;