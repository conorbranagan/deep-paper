import React, { useState } from 'react';
import { Button } from './ui/button';
import { PlusIcon, XIcon, ChevronRightIcon, SearchIcon, NotepadTextIcon } from 'lucide-react';
import { ResearchTab } from './types';
import { ModelOption, modelOptions } from './lib/modelOptions';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

interface ResearchSidebarProps {
  activeTabID: string;
  tabs: ResearchTab[];
  onTabClick: (tabId: string) => void;
  onAddTab: () => void;
  onDeleteTab: (tabId: string) => void;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  onExploreClick: () => void;
  selectedModel: string;
  onModelChange: (modelId: string) => void;
}

export default function ResearchSidebar({
  activeTabID,
  tabs,
  onTabClick,
  onAddTab,
  onDeleteTab,
  isOpen,
  setIsOpen,
  onExploreClick,
  selectedModel,
  onModelChange
}: ResearchSidebarProps) {
  const [isHovering, setIsHovering] = useState(false);

  // Handle hover events
  const handleMouseEnter = () => {
    setIsHovering(true);
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
  };

  // Determine if sidebar should be visible
  const shouldShow = isOpen || isHovering;

  return (
    <div className={`h-full ${isOpen ? 'relative' : 'absolute'}`}>
      {/* Hover area when sidebar is closed */}
      {!isOpen && (
        <div
          className="absolute left-0 top-0 w-14 h-full z-10 border-style:dotted"
          onMouseEnter={handleMouseEnter}
        />
      )}

      <button
        className={`absolute top-4 ${isOpen ? 'left-64 -ml-3' : 'left-6'} z-20 bg-white rounded-full p-1 shadow-md`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <ChevronRightIcon className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <div
        className={`w-64 bg-gray-100 border-r border-gray-200 flex flex-col h-full transition-all duration-300 ease-in-out ${shouldShow ? 'translate-x-0 opacity-100  shadow-lg' : '-translate-x-full opacity-0'
          } ${!isOpen ? 'pt-12' : ''}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Explore Section */}
        <div
          className={`p-4 border-b border-gray-200 cursor-pointer hover:bg-gray-200 transition-colors ${activeTabID === 'explore' ? 'bg-blue-50' : ''
            }`}
          onClick={onExploreClick}
        >
          <div className="flex items-center">
            <SearchIcon className="h-4 w-4 mr-2" />
            <h2 className="font-semibold">Explore</h2>
          </div>
        </div>

        {/* In Review Section */}
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <div className="flex items-center">
            <NotepadTextIcon className="h-4 w-4 mr-2" />
            <h2 className="font-semibold">In Review</h2>
          </div>
          <Button
            onClick={onAddTab}
            variant="secondary"
            size="sm"
            className="cursor-pointer mr-1"
            title="Add paper"
          >
            <PlusIcon />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              title={tab.title}
              className={`
                relative group px-4 py-3 cursor-pointer border-l-4 flex items-center justify-between text-sm
                ${activeTabID === tab.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-transparent hover:bg-gray-50'}
              `}
              onClick={() => onTabClick(tab.id)}
            >
              <div className="flex items-center overflow-hidden">
                {tab.isLoading && (
                  <div className="mr-2 h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                )}
                <span className="truncate">
                  {tab.title || <em>New Paper</em>}
                </span>
              </div>

              <button
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-full hover:bg-gray-200"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteTab(tab.id);
                }}
                aria-label="Close tab"
              >
                <XIcon className="h-4 w-4 text-gray-500" />
              </button>
            </div>
          ))}
        </div>

        {/* Model Selection */}
        <div className="p-4 border-b border-gray-200">
          <Select
            value={selectedModel}
            onValueChange={onModelChange}
          >
            <SelectTrigger className="w-full">
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
        </div>
      </div>
    </div>
  );
}