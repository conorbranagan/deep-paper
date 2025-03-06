import React from 'react';
import { Button } from './ui/button';
import { PlusIcon, XIcon } from 'lucide-react';
import { ResearchTab } from './types';

interface ResearchSidebarProps {
  activeTabID: string;
  tabs: ResearchTab[];
  onTabClick: (tabId: string) => void;
  onAddTab: () => void;
  onDeleteTab: (tabId: string) => void;
}

export default function ResearchSidebar({
  activeTabID,
  tabs,
  onTabClick,
  onAddTab,
  onDeleteTab
}: ResearchSidebarProps) {
  return (
    <div className="w-64 bg-gray-100 border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200 flex justify-between items-center">
        <h2 className="font-semibold">Papers</h2>
        <Button
          onClick={onAddTab}
          variant="secondary"
          size="xs"
          className="cursor-pointer"
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
              relative group px-4 py-3 cursor-pointer border-l-4 flex items-center justify-between
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
    </div>
  );
}