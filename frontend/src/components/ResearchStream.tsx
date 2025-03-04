import React from 'react';
import MarkdownRenderer from './ui/markdown';

interface ResearchStreamProps {
  data: Array<{
    type: string;
    content: string;
  }>;
}

export default function ResearchStream({ data }: ResearchStreamProps) {
  // Helper function to get appropriate styling for each content type
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

  // Helper function to get icon and label for each content type
  const getTypeDetails = (type: string) => {
    switch (type) {
      case 'thought':
        return { 
          icon: '💭', 
          label: 'Thinking' 
        };
      case 'action':
        return { 
          icon: '⚙️', 
          label: 'Action' 
        };
      case 'result':
        return { 
          icon: '📊', 
          label: 'Result' 
        };
      case 'summary':
        return { 
          icon: '📝', 
          label: 'Summary' 
        };
      case 'error':
        return { 
          icon: '❌', 
          label: 'Error' 
        };
      case 'user-question':
        return { 
          icon: '❓', 
          label: 'Your Question' 
        };
      case 'agent-answer':
        return { 
          icon: '🤖', 
          label: 'Answer' 
        };
      default:
        return { 
          icon: 'ℹ️', 
          label: 'Info' 
        };
    }
  };

  return (
    <div className="space-y-4">
      {data.map((item, index) => {
        const { icon, label } = getTypeDetails(item.type);
        const contentStyle = getContentStyle(item.type);
        
        return (
          <div 
            key={index} 
            className={`border rounded-md p-4 ${contentStyle}`}
          >
            <div className="flex items-center mb-2">
              <span className="mr-2">{icon}</span>
              <span className="font-medium">{label}</span>
            </div>
            <div className="prose max-w-none">
              <MarkdownRenderer>{item.content}</MarkdownRenderer>
            </div>
          </div>
        );
      })}
    </div>
  );
}

