export interface Topic {
  id: string;
  slug: string;
  title: string;
  category: string;
  tags?: string[];
  entry_count: number;
  total_upvotes: number;
  total_downvotes: number;
  comment_count: number;
  trending_score: number;
  last_entry_at?: string;
  created_at: string;
}

export interface GundemResponse {
  topics: Topic[];
  pagination: { limit: number; offset: number; total?: number };
}

export interface TopicResponse {
  topic: Topic;
  entries: import('./entry.model').Entry[];
  pagination: { limit: number; offset: number; total: number };
}
