"use client";

import { useState } from "react";
import { Button } from "./ui/button";

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  disabled: boolean;
  placeholder: string;
}

export default function QuestionInput({
  onSubmit,
  disabled,
  placeholder,
}: QuestionInputProps) {
  const [question, setQuestion] = useState<string>("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      onSubmit(question);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={placeholder}
          className="flex-grow px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={disabled}
        />
        <Button
          type="submit"
          disabled={disabled || !question.trim()}
          className="px-6 py-2 rounded font-medium"
          variant="default"
        >
          Ask
        </Button>
      </div>
    </form>
  );
}
