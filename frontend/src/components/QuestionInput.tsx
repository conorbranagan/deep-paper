'use client';

import { useState } from 'react';

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const QuestionInput: React.FC<QuestionInputProps> = ({
  onSubmit,
  disabled = false,
  placeholder = "Ask a question..."
}) => {
  const [question, setQuestion] = useState<string>('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && !disabled) {
      onSubmit(question);
      setQuestion('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={placeholder}
        className="flex-grow px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        disabled={disabled}
      />
      <button
        type="submit"
        disabled={disabled || !question.trim()}
        className={`px-4 py-2 rounded font-medium ${
          disabled || !question.trim()
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 text-white'
        }`}
      >
        Ask
      </button>
    </form>
  );
};

export default QuestionInput;