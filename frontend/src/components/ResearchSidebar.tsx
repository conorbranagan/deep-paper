import React from 'react';
import { PlusIcon } from '@heroicons/react/24/outline';

export interface ResearchTab {
  id: string;
  title?: string;
  isLoading: boolean;
}

interface ResearchSidebarProps {
  tabs: ResearchTab[];
  activeTabID: string;
  onTabClick: (tabId: string) => void;
  onAddTab: () => void;
}

const ResearchSidebar: React.FC<ResearchSidebarProps> = ({
  tabs,
  activeTabID,
  onTabClick,
  onAddTab,
}) => {
  return (
    <div className="w-64 bg-gray-100 h-screen p-4 border-r border-gray-200 flex flex-col">
      <h2 className="text-lg font-semibold mb-4">Papers</h2>
      
      <div className="flex-grow overflow-y-auto">
        <ul className="space-y-2">
          {tabs.map((tab) => (
            <li
              key={tab.id}
              className={`p-2 rounded cursor-pointer flex items-center justify-between ${
                tab.id === activeTabID ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-200'
              }`}
              onClick={() => onTabClick(tab.id)}
            >
              <div className="truncate flex-grow">
                {tab.title || <em>Pending...</em>}
              </div>
              {tab.isLoading && (
                <div className="ml-2 animate-spin h-4 w-4 border-2 border-blue-500 rounded-full border-t-transparent"></div>
              )}
            </li>
          ))}
          
          <li 
            className="p-2 rounded cursor-pointer hover:bg-gray-200 text-gray-600 flex items-center mt-2"
            onClick={onAddTab}
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            <span>Add Paper</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default ResearchSidebar; 