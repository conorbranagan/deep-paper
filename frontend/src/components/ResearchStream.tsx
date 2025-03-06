'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent } from './ui/card';
import ResearchStreamItem from './ResearchStreamItem';

interface ResearchStreamData {
  type: string;
  content: string;
}

interface ResearchStreamProps {
  url: string;
  model: string;
  question?: string;
}

const getContentStyle = (type: string) => {
  switch (type) {
    case 'thought':
      return 'bg-purple-50 border-purple-200 text-purple-800';
    case 'action':
      return 'bg-yellow-50 border-yellow-200 text-yellow-800';
    case 'result':
      return 'bg-green-50 border-green-200 text-green-800';
    case 'summary':
      return 'bg-blue-50 border-blue-200 text-blue-800';
    case 'error':
      return 'bg-red-50 border-red-200 text-red-800';
    case 'user-question':
      return 'bg-gray-100 border-gray-300 text-gray-800';
    case 'agent-answer':
      return 'bg-blue-50 border-blue-200 text-blue-800';
    default:
      return 'bg-gray-50 border-gray-200 text-gray-800';
  }
};

export default function ResearchStream({
  url,
  model,
  question
}: ResearchStreamProps) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const [researchStream, setResearchStream] = useState<ResearchStreamData[]>([]);
  const [isResearching, setIsResearching] = useState<boolean>(false);

  useEffect(() => {
    // Clean up function to close EventSource when component unmounts
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    if (!question) {
      return;
    }

    // Start researching a document.
    setIsResearching(true);
    setResearchStream([]);
    try {
      const searchParams = new URLSearchParams({
        url: url,
        question: question,
        model: model
      });

      const deepURL = `${process.env.NEXT_PUBLIC_API_URL}/api/research/deep?${searchParams.toString()}`;

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      eventSourceRef.current = new EventSource(deepURL);

      eventSourceRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'complete') {
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
            setIsResearching(false);
          } else if (data.type === 'error') {
            throw new Error(data.content || 'An error occurred');
          } else {
            setResearchStream((prev: ResearchStreamData[]) => [...prev, data]);
          }
        } catch (error) {
          console.error('Error parsing stream data:', error);
          setResearchStream((prev: ResearchStreamData[]) => [
            ...prev,
            {
              type: 'error',
              content: 'Failed to process your research question. Please try again.'
            }
          ]);
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
          setIsResearching(false);
        }
      };

      eventSourceRef.current.onerror = () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        setIsResearching(false);
      };
    } catch (error) {
      console.error('Deep research error:', error);
      setResearchStream((prev: ResearchStreamData[]) => [
        ...prev,
        {
          type: 'error',
          content: 'Failed to process your research question. Please try again.'
        }
      ]);
      setIsResearching(false);
    }
  }, [question, model, url]);


  return (
    <>
      {researchStream.length > 0 && (
        <Card className="mt-6">
          <CardContent className="pt-6">
            {researchStream.map((item, index) => (
              <div
                key={index}
                className={`border rounded-md p-4 mb-4 ${getContentStyle(item.type)}`}
              >
                <ResearchStreamItem key={index} type={item.type} content={item.content} />
              </div>
            ))}
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
          <div className="ml-3 text-sm text-gray-600">
            Researching your question...
          </div>
        </div>
      )}
    </>
  );
}

