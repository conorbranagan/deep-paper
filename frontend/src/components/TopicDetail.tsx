'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent } from './ui/card';
import { ExternalLink, BookOpen } from 'lucide-react';
import MarkdownRenderer from './ui/markdown';
import { Topic } from './types';


interface TopicDetailProps {
  topic: Topic;
  paperUrl?: string;
  model: string;
  onResearchPaper?: (url: string) => void;
}

const TopicDetail: React.FC<TopicDetailProps> = ({ topic, paperUrl, model, onResearchPaper }) => {
  const [topicContent, setTopicContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const streamEndRef = useRef<HTMLDivElement>(null);

  const loadTopicSummary = useCallback(
    async (eventSource: EventSource) => {
      if (!paperUrl) return;

      setIsLoading(true);
      setError('');
      setTopicContent('');

      try {
        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'content') {
              setTopicContent(prev => prev + data.content);
            } else if (data.type === 'complete') {
              eventSource.close();
              setIsLoading(false);
            } else if (data.type === 'error') {
              throw new Error(data.content || 'An error occurred');
            }
          } catch (error) {
            console.error('Error parsing stream data:', error);
            setError('Failed to process topic summary');
            eventSource.close();
            setIsLoading(false);
          }
        };

        eventSource.onerror = () => {
          eventSource.close();
          setIsLoading(false);
        };

      } catch (error) {
        console.error('Topic summary error:', error);
        setError('Failed to load topic summary');
        setIsLoading(false);
      }
    }, [paperUrl]);

  useEffect(() => {
    let eventSource: EventSource;

    if (paperUrl && topic) {
      const encodedUrl = encodeURIComponent(paperUrl);
      const encodedTopic = encodeURIComponent(topic.topic);
      const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/research/paper/topic?url=${encodedUrl}&topic=${encodedTopic}&model=${model}`;
      eventSource = new EventSource(apiUrl);
      loadTopicSummary(eventSource);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [paperUrl, topic, model, loadTopicSummary]);

  const isArxivUrl = (url: string): boolean => {
    return url.startsWith('https://arxiv.org/abs');
  };

  if (!topic) {
    return <p>No topic selected.</p>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-6">
          {isLoading && topicContent.length === 0 && (
            <div className="flex items-center justify-center py-4">
              <div className="animate-pulse flex space-x-2">
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
                <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
              </div>
              <div className="ml-4">Analyzing topic...</div>
            </div>
          )}

          {error && <p className="text-red-500 mb-4">{error}</p>}

          <div className="prose max-w-none">
            <MarkdownRenderer>{topicContent}</MarkdownRenderer>


            {isLoading && topicContent.length > 0 && (
              <div className="animate-pulse flex space-x-2 my-2">
                <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
                <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
                <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
              </div>
            )}
          </div>

          <div ref={streamEndRef} />
        </CardContent>
      </Card>

      {/* Further Reading Section */}
      <div>
        <h3 className="text-xl font-semibold mb-4">Further Reading</h3>
        {topic.further_reading && topic.further_reading.length > 0 ? (
          <div className="space-y-3">
            {topic.further_reading.map((paper, index) => (
              <div
                key={index}
                className="p-4 border rounded-lg bg-white hover:bg-gray-50 transition-colors duration-200"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium text-blue-600">
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline"
                      >
                        {paper.title}
                      </a>
                    </h4>
                    <p className="text-gray-600 text-sm">{paper.author} ({paper.year})</p>
                  </div>
                  <div className="flex space-x-2">
                    {isArxivUrl(paper.url) && onResearchPaper && (
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => {
                          e.preventDefault();
                          onResearchPaper(paper.url);
                        }}
                        className="text-gray-400 hover:text-gray-600"
                        title="Research this topic"
                      >
                        <BookOpen className="h-4 w-4 flex-shrink-0 mt-1" />
                      </a>
                    )}
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <ExternalLink className="h-4 w-4 flex-shrink-0 mt-1" />
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No further reading available for this topic.</p>
        )}
      </div>
    </div>
  );
};

export default TopicDetail;