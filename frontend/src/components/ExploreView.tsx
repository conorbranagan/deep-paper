'use client';

import React, { useState } from 'react';
import { Button } from './ui/button';
import MarkdownRenderer from './ui/markdown';

interface Paper {
  id: string;
  title: string;
  authors: string[];
  url: string;
  relevance: string;
  year: string;
}

interface ExploreViewProps {
  onResearchPaper: (url: string) => void;
}

// Fake data for development
const FAKE_PAPERS: Record<string, Paper[]> = {
  "machine learning": [
    {
      id: "2006.11239",
      title: "Self-Supervised Learning: Generative or Contrastive",
      authors: ["Xiao Liu", "Fanjin Zhang", "Zhenyu Hou", "Zhaoyu Wang", "Jing Zhang", "Jie Tang"],
      url: "https://arxiv.org/abs/2006.11239",
      relevance: "This paper provides a comprehensive survey of self-supervised learning methods in machine learning, comparing generative and contrastive approaches. It's highly relevant to your search as it offers a systematic overview of recent advances in the field.",
      year: "2020"
    },
    {
      id: "1706.03762",
      title: "Attention Is All You Need",
      authors: ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Łukasz Kaiser", "Illia Polosukhin"],
      url: "https://arxiv.org/abs/1706.03762",
      relevance: "This seminal paper introduced the Transformer architecture which has become fundamental to modern machine learning, especially in NLP. The attention mechanism described here has influenced countless subsequent ML models.",
      year: "2017"
    },
    {
      id: "1905.11946",
      title: "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
      authors: ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
      url: "https://arxiv.org/abs/1905.11946",
      relevance: "BERT revolutionized natural language processing by introducing a pre-training approach that has become standard in machine learning for language tasks. This paper is essential for understanding modern ML approaches to NLP.",
      year: "2019"
    }
  ],
  "quantum computing": [
    {
      id: "1801.00862",
      title: "Quantum Computing in the NISQ era and beyond",
      authors: ["John Preskill"],
      url: "https://arxiv.org/abs/1801.00862",
      relevance: "This influential paper by John Preskill introduced the concept of 'Noisy Intermediate-Scale Quantum' (NISQ) computing, which has become a central framework for understanding the current state and near-term future of quantum computing research.",
      year: "2018"
    },
    {
      id: "1905.07047",
      title: "Quantum Supremacy using a Programmable Superconducting Processor",
      authors: ["Frank Arute", "Kunal Arya", "Ryan Babbush", "et al."],
      url: "https://arxiv.org/abs/1905.07047",
      relevance: "This paper from Google AI Quantum describes the first experimental demonstration of quantum supremacy, a milestone in quantum computing where a quantum computer performed a specific calculation that is infeasible for classical computers.",
      year: "2019"
    },
    {
      id: "1710.01437",
      title: "Quantum Machine Learning",
      authors: ["Jacob Biamonte", "Peter Wittek", "Nicola Pancotti", "Patrick Rebentrost", "Nathan Wiebe", "Seth Lloyd"],
      url: "https://arxiv.org/abs/1710.01437",
      relevance: "This review paper explores the intersection of quantum computing and machine learning, discussing how quantum algorithms might enhance machine learning tasks and how machine learning might help with quantum computing challenges.",
      year: "2017"
    }
  ],
  "climate change": [
    {
      id: "2106.08668",
      title: "Tackling Climate Change with Machine Learning",
      authors: ["David Rolnick", "Priya L. Donti", "Lynn H. Kaack", "Kelly Kochanski", "Alexandre Lacoste", "Kris Sankaran", "Andrew Slavin Ross", "Nikola Milojevic-Dupont", "Natasha Jaques", "Anna Waldman-Brown", "et al."],
      url: "https://arxiv.org/abs/2106.08668",
      relevance: "This comprehensive paper reviews how machine learning can be applied to address climate change across various domains including electricity systems, transportation, and climate science. It's directly relevant to research on technological approaches to climate challenges.",
      year: "2021"
    },
    {
      id: "2010.03596",
      title: "Climate Change and the Re-Evaluation of Cost-Benefit Analysis",
      authors: ["Jonathan S. Masur", "Eric A. Posner"],
      url: "https://arxiv.org/abs/2010.03596",
      relevance: "This paper examines how climate change challenges traditional economic cost-benefit analysis frameworks, which is crucial for understanding policy approaches to climate change mitigation and adaptation.",
      year: "2020"
    },
    {
      id: "1912.01415",
      title: "Towards a Climate Mathematics",
      authors: ["Christopher Pattison", "Alyssa M. Adams", "Brent Sherwood", "Tushar Mittal", "Bryan Norton", "David H. Wolpert"],
      url: "https://arxiv.org/abs/1912.01415",
      relevance: "This paper proposes new mathematical frameworks specifically designed for climate science, which could improve climate modeling and prediction capabilities.",
      year: "2019"
    }
  ]
};

// Default fallback papers for searches without matches
const DEFAULT_PAPERS: Paper[] = [
  {
    id: "2103.13630",
    title: "Ethical and social risks of harm from Language Models",
    authors: ["Laura Weidinger", "John Mellor", "Maribeth Rauh", "Conor Griffin", "Jonathan Uesato", "Po-Sen Huang", "Myra Cheng", "Mia Glaese", "Borja Balle", "Atoosa Kasirzadeh", "et al."],
    url: "https://arxiv.org/abs/2103.13630",
    relevance: "This paper discusses potential risks and harms from large language models, which is relevant to many research areas in AI and computing.",
    year: "2021"
  },
  {
    id: "2101.00027",
    title: "A Survey of Deep Learning for Scientific Discovery",
    authors: ["Maithra Raghu", "Eric Schmidt"],
    url: "https://arxiv.org/abs/2101.00027",
    relevance: "This survey covers applications of deep learning across multiple scientific domains, making it broadly relevant to many research interests.",
    year: "2021"
  }
];

const ExploreView: React.FC<ExploreViewProps> = ({ onResearchPaper }) => {
  const [query, setQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<Paper[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Please enter a research topic');
      return;
    }
    
    setIsLoading(true);
    setError('');
    
    // Simulate API call with a timeout
    setTimeout(() => {
      try {
        // Find the closest matching key in our fake data
        const normalizedQuery = query.toLowerCase().trim();
        let matchedPapers: Paper[] = [];
        
        // Check for exact matches first
        Object.keys(FAKE_PAPERS).forEach(key => {
          if (normalizedQuery.includes(key) || key.includes(normalizedQuery)) {
            matchedPapers = FAKE_PAPERS[key];
          }
        });
        
        // If no matches, use default papers
        if (matchedPapers.length === 0) {
          matchedPapers = DEFAULT_PAPERS;
        }
        
        setSearchResults(matchedPapers);
        setHasSearched(true);
        setIsLoading(false);
      } catch (error) {
        console.error('Explore search error:', error);
        setError('Failed to search for papers. Please try again.');
        setIsLoading(false);
      }
    }, 1500); // Simulate network delay
    
    // Commented out actual API call for future implementation
    /*
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/research/explore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch research papers');
      }
      
      const data = await response.json();
      setSearchResults(data.papers);
      setHasSearched(true);
    } catch (error) {
      console.error('Explore search error:', error);
      setError('Failed to search for papers. Please try again.');
    } finally {
      setIsLoading(false);
    }
    */
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className={`transition-all duration-300 ${hasSearched ? 'mb-8' : 'mb-32'}`}>
        <h1 className={`font-bold text-center transition-all duration-300 ${hasSearched ? 'text-2xl mb-4' : 'text-4xl mb-12'}`}>
          Explore
        </h1>
        
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a research topic, question, or field of interest..."
            className="flex-grow px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg"
            disabled={isLoading}
          />
          <Button
            type="submit"
            disabled={isLoading}
            className="px-6 py-3 rounded-lg font-medium"
          >
            {isLoading ? 'Searching...' : 'Search'}
          </Button>
        </form>
        
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-pulse flex space-x-2">
            <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
            <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
            <div className="h-3 w-3 bg-blue-600 rounded-full"></div>
          </div>
          <div className="ml-4">Searching for relevant papers...</div>
        </div>
      )}

      {hasSearched && !isLoading && searchResults.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-6">Top Papers on "{query}"</h2>
          <div className="space-y-6">
            {searchResults.map((paper) => (
              <div key={paper.id} className="border rounded-lg p-6 bg-white shadow-sm hover:shadow-md transition-shadow">
                <h3 className="text-xl font-bold mb-2">
                  <a href={paper.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {paper.title}
                  </a>
                </h3>
                <p className="text-gray-600 mb-4">
                  {paper.authors.join(', ')} ({paper.year})
                </p>
                <div className="mb-4">
                  <h4 className="font-semibold mb-2">Why it's relevant:</h4>
                  <MarkdownRenderer>{paper.relevance}</MarkdownRenderer>
                </div>
                <Button 
                  onClick={() => onResearchPaper(paper.url)}
                  className="mt-2"
                >
                  Research This Paper
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasSearched && !isLoading && searchResults.length === 0 && (
        <div className="text-center py-12">
          <p className="text-xl text-gray-600">No papers found for "{query}". Try a different search term.</p>
        </div>
      )}
    </div>
  );
};

export default ExploreView; 