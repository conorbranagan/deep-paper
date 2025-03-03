import { useState } from 'react';

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  disabled: boolean;
}

export default function QuestionInput({ onSubmit, disabled }: QuestionInputProps) {
  const [question, setQuestion] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && !disabled) {
      onSubmit(question);
      setQuestion('');
    }
  };

  return (
    <div className="border rounded-lg p-4 bg-white">
      <h3 className="text-lg font-medium mb-2">Ask a question about this paper</h3>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={disabled 
            ? "Start research to ask questions..." 
            : "What would you like to know about this paper?"}
          className="flex-grow px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={disabled}
        />
        <button
          type="submit"
          disabled={disabled || !question.trim()}
          className={`px-6 py-2 rounded font-medium ${
            disabled || !question.trim()
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white'
          }`}
        >
          Ask
        </button>
      </form>
    </div>
  );
}
