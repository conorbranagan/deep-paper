'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent } from './ui/card';
import { ExternalLink } from 'lucide-react';
import MarkdownRenderer from './ui/markdown';

interface FurtherReading {
  title: string;
  author: string;
  year: number;
  url: string;
}

interface Topic {
  topic: string;
  summary: string;
  further_reading: FurtherReading[];
}

interface TopicDetailProps {
  topic: Topic;
  paperUrl?: string;
}

const TopicDetail: React.FC<TopicDetailProps> = ({ topic, paperUrl }) => {
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
      // Encode both URL and topic name for the API call
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
        //setError('Connection error. Please try again.');
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
      // Your EventSource setup code
      const encodedUrl = encodeURIComponent(paperUrl);
      const encodedTopic = encodeURIComponent(topic.topic);
      const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/research/summarize/topic?url=${encodedUrl}&topic=${encodedTopic}`;
      eventSource = new EventSource(apiUrl);
      loadTopicSummary(eventSource);
    }

    // Cleanup function
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [paperUrl, topic, loadTopicSummary]);

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
              <a
                key={index}
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-4 border rounded-lg bg-white hover:bg-gray-50 transition-colors duration-200"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium text-blue-600">{paper.title}</h4>
                    <p className="text-gray-600 text-sm">{paper.author} ({paper.year})</p>
                  </div>
                  <ExternalLink className="text-gray-400 h-4 w-4 flex-shrink-0 mt-1" />
                </div>
              </a>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No further reading available for this topic.</p>
        )}
      </div>

      {/* Placeholder for future features */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-gray-50">
          <CardContent className="pt-6">
            <h3 className="text-lg font-semibold mb-2">Related Papers</h3>
            <p className="text-gray-500 text-sm">Explore papers related to this topic.</p>
            <button className="mt-3 text-blue-600 text-sm disabled:opacity-50" disabled>
              Coming soon →
            </button>
          </CardContent>
        </Card>

        <Card className="bg-gray-50">
          <CardContent className="pt-6">
            <h3 className="text-lg font-semibold mb-2">Save Insights</h3>
            <p className="text-gray-500 text-sm">
              Save highlights and notes about this topic.
            </p>
            <button className="mt-3 text-blue-600 text-sm disabled:opacity-50" disabled>
              Coming soon →
            </button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default TopicDetail;