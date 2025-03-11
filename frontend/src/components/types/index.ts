export interface FurtherReading {
  title: string;
  author: string;
  year: number;
  url: string;
}

export interface Topic {
  topic: string;
  summary: string;
  further_reading: FurtherReading[];
}

export interface ResearchTab {
  id: string;
  title?: string;
  isLoading: boolean;
  initialUrl?: string;
}
