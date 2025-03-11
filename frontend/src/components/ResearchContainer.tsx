'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Researcher from './Researcher';
import ResearchSidebar from './ResearchSidebar';
import ExploreView from './ExploreView';
import { ResearchTab } from './types';
import { v4 as uuidv4 } from 'uuid';

export default function ResearchContainer() {
  const [tabs, setTabs] = useState<ResearchTab[]>([]);
  const [activeTabID, setActiveTabID] = useState<string>('explore');
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);

  // Load tabs from localStorage on initial render
  useEffect(() => {
    const savedTabs = localStorage.getItem('research-tabs');
    const savedActiveTabID = localStorage.getItem('research-active-tab');
    const savedSidebarState = localStorage.getItem('research-sidebar-open');

    if (savedSidebarState !== null) {
      setIsSidebarOpen(savedSidebarState === 'true');
    }

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

  // Save sidebar state to localStorage
  useEffect(() => {
    localStorage.setItem('research-sidebar-open', String(isSidebarOpen));
  }, [isSidebarOpen]);

  // Save tabs to localStorage whenever they change
  useEffect(() => {
    if (tabs.length > 0) {
      const finishedTabs = tabs.filter(tab => !tab.isLoading && tab.title).map(tab => ({
        id: tab.id,
        title: tab.title,
      }));
      localStorage.setItem('research-tabs', JSON.stringify(finishedTabs));
    }
  }, [tabs]);

  // Save active tab ID to localStorage whenever it changes
  useEffect(() => {
    const activeTab = tabs.find(tab => tab.id === activeTabID);
    if (activeTab && !activeTab.isLoading && activeTab.title) {
      localStorage.setItem('research-active-tab', activeTabID);
    }
  }, [tabs, activeTabID]);

  const generateTabID = useCallback(() => {
    // Always add to the latest tab number to avoid re-use.
    const latestTab = tabs[tabs.length - 1];
    return `tab-${parseInt(latestTab.id.split('-')[1], 10) + 1}`;
  }, [tabs]);

  const onResearchPaper = useCallback((url: string) => {
    if (url) {
      const newTab: ResearchTab = {
        id: generateTabID(),
        isLoading: false,
        initialUrl: url
      };
      setTabs(prevTabs => [...prevTabs, newTab]);
    }
  }, [generateTabID]);

  const initializeDefaultTab = () => {
    const defaultTab: ResearchTab = {
      id: 'tab-1',
      isLoading: false
    };
    setTabs([defaultTab]);
    setActiveTabID(defaultTab.id);
  };

  const handleAddTab = () => {
    const newTabId = uuidv4();
    setTabs([...tabs, { id: newTabId, title: '', isLoading: false }]);
    setActiveTabID(newTabId);
  };

  const handleDeleteTab = (tabId: string) => {
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
        setActiveTabID('explore');
        return [defaultTab];
      }

      return newTabs;
    });
  };

  const handleLoadingChange = useCallback((tabId: string, isLoading: boolean) => {
    setTabs(prevTabs =>
      prevTabs.map(tab =>
        tab.id === tabId ? { ...tab, isLoading } : tab
      )
    );
  }, []);

  const handleTitleChange = useCallback((tabId: string, title: string) => {
    if (!title) return;

    setTabs(prevTabs =>
      prevTabs.map(tab =>
        tab.id === tabId ? { ...tab, title: title || tab.title } : tab
      )
    );
  }, []);

  const handleExploreClick = () => {
    setActiveTabID('explore');
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <ResearchSidebar
        activeTabID={activeTabID}
        tabs={tabs}
        onTabClick={setActiveTabID}
        onAddTab={handleAddTab}
        onDeleteTab={handleDeleteTab}
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        onExploreClick={handleExploreClick}
      />

      <div className={`flex-1 overflow-y-auto transition-all duration-300 ${!isSidebarOpen ? 'ml-0' : ''}`}>
        {activeTabID === 'explore' ? (
          <ExploreView onResearchPaper={onResearchPaper} />
        ) : (
          <Researcher
            key={tabs.find(tab => tab.id === activeTabID)?.id}
            tabId={activeTabID}
            onLoadingChange={handleLoadingChange}
            onTitleChange={handleTitleChange}
            onResearchPaper={onResearchPaper}
            initialUrl={tabs.find(tab => tab.id === activeTabID)?.initialUrl}
          />
        )}
      </div>
    </div>
  );
}
