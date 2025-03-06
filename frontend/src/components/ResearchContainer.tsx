'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Researcher from './Researcher';
import ResearchSidebar, { ResearchTab } from './ResearchSidebar';

export default function ResearchContainer() {
  const [tabs, setTabs] = useState<ResearchTab[]>([]);
  const [activeTabID, setActiveTabID] = useState<string>('');

  // Load tabs from localStorage on initial render
  useEffect(() => {
    const savedTabs = localStorage.getItem('research-tabs');
    const savedActiveTabID = localStorage.getItem('research-active-tab');

    if (savedTabs) {
      try {
        const parsedTabs = JSON.parse(savedTabs);
        setTabs(parsedTabs);

        if (savedActiveTabID) {
          setActiveTabID(savedActiveTabID);
        } else if (parsedTabs.length > 0) {
          setActiveTabID(parsedTabs[0].id);
        }
      } catch (error) {
        console.error('Error loading tabs from localStorage:', error);
        initializeDefaultTab();
      }
    } else {
      initializeDefaultTab();
    }
  }, []);

  // Save tabs to localStorage whenever they change
  useEffect(() => {
    if (tabs.length > 0) {
      localStorage.setItem('research-tabs', JSON.stringify(tabs));
    }
  }, [tabs]);

  // Save active tab ID to localStorage whenever it changes
  useEffect(() => {
    if (activeTabID) {
      localStorage.setItem('research-active-tab', activeTabID);
    }
  }, [activeTabID]);

  const initializeDefaultTab = () => {
    const defaultTab: ResearchTab = {
      id: 'tab-1',
      isLoading: false
    };
    setTabs([defaultTab]);
    setActiveTabID(defaultTab.id);
  };

  const generateTabID = () => {
    // Create a deterministic ID based on the current number of tabs
    return `tab-${tabs.length + 1}`;
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

  const handleDeleteTab = useCallback((tabId: string) => {
    // Remove the tab's research state from localStorage
    localStorage.removeItem(`research-state-${tabId}`);

    // Update tabs state
    setTabs(prevTabs => {
      const newTabs = prevTabs.filter(tab => tab.id !== tabId);

      // If we're deleting the active tab, we need to activate another tab
      if (tabId === activeTabID && newTabs.length > 0) {
        // Activate the previous tab, or the first tab if there is no previous tab
        const deletedTabIndex = prevTabs.findIndex(tab => tab.id === tabId);
        const newActiveIndex = Math.max(0, deletedTabIndex - 1);
        setActiveTabID(newTabs[newActiveIndex].id);
      } else if (newTabs.length === 0) {
        // If we deleted the last tab, create a new default tab
        const defaultTab: ResearchTab = {
          id: 'tab-1',
          isLoading: false
        };
        setActiveTabID(defaultTab.id);
        return [defaultTab];
      }

      return newTabs;
    });
  }, [activeTabID]);

  return (
    <div className="flex h-screen overflow-hidden">
      <ResearchSidebar
        activeTabID={activeTabID}
        tabs={tabs}
        onTabClick={setActiveTabID}
        onAddTab={handleAddTab}
        onDeleteTab={handleDeleteTab}
      />

      <div className="flex-1 overflow-y-auto">
        {tabs.map(tab => (
          <div
            key={tab.id}
            className={`h-full ${activeTabID === tab.id ? 'block' : 'hidden'}`}
          >
            <Researcher
              key={tab.id}
              tabId={tab.id}
              onLoadingChange={(isLoading: boolean) => handleLoadingChange(isLoading, tab.id)}
              onTitleChange={(title: string) => handleTitleChange(title, tab.id)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
