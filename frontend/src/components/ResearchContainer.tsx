'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Researcher from './Researcher';
import ResearchSidebar, { ResearchTab } from './ResearchSidebar';

export default function ResearchContainer() {
  const [tabs, setTabs] = useState<ResearchTab[]>([]);
  const [activeTabID, setActiveTabID] = useState<string>('');

  // Initialize with a default tab
  useEffect(() => {
    if (tabs.length === 0) {
      const defaultTab: ResearchTab = {
        id: generateTabID(),
        isLoading: false
      };
      setTabs([defaultTab]);
      setActiveTabID(defaultTab.id);
    }
  }, [tabs.length]);

  const generateTabID = () => {
    return Math.random().toString(36).substring(2, 9);
  };

  const handleAddTab = () => {
    const newTab: ResearchTab = {
      id: generateTabID(),
      isLoading: false
    };
    setTabs(prevTabs => [...prevTabs, newTab]);
    setActiveTabID(newTab.id);
  };

  const handleLoadingChange = useCallback((isLoading: boolean, tabId: string) => {
    setTabs(prevTabs => 
      prevTabs.map(tab => 
        tab.id === tabId ? { ...tab, isLoading } : tab
      )
    );
  }, []);

  const handleTitleChange = useCallback((title: string, tabId: string) => {
    if (!title) return;
    
    setTabs(prevTabs => 
      prevTabs.map(tab => 
        tab.id === tabId ? { ...tab, title: title || tab.title } : tab
      )
    );
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <ResearchSidebar 
        activeTabID={activeTabID}
        tabs={tabs}
        onTabClick={setActiveTabID}
        onAddTab={handleAddTab}
      />
      
      <div className="flex-1 overflow-y-auto">
        {tabs.map(tab => (
          <div 
            key={tab.id} 
            className={`h-full ${activeTabID === tab.id ? 'block' : 'hidden'}`}
          >
            <Researcher 
              key={tab.id}
              onLoadingChange={(isLoading: boolean) => handleLoadingChange(isLoading, tab.id)}
              onTitleChange={(title: string) => handleTitleChange(title, tab.id)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
