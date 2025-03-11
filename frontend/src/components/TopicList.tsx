"use client";

import React from "react";
import { Topic } from "./types";

interface TopicListProps {
  topics: Topic[];
  onTopicSelect: (topic: Topic) => void;
}

const TopicList: React.FC<TopicListProps> = ({ topics, onTopicSelect }) => {
  if (!topics || topics.length === 0) {
    return <p>No topics available for this paper.</p>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {topics.map((topic, index) => (
        <button
          key={index}
          onClick={() => onTopicSelect(topic)}
          className="text-left p-4 border rounded-lg bg-white hover:bg-blue-50 transition-colors duration-200 shadow-sm hover:shadow cursor-pointer"
        >
          <h3 className="font-semibold text-lg mb-2">{topic.topic}</h3>
          <p className="text-gray-600 text-sm line-clamp-3">{topic.summary}</p>
          <div className="mt-3 text-blue-600 text-sm">Explore this topic →</div>
        </button>
      ))}
    </div>
  );
};

export default TopicList;
