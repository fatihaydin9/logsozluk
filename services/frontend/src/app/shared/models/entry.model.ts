import { Agent } from './agent.model';
import { Topic } from './topic.model';

export interface Entry {
  id: string;
  topic_id: string;
  agent_id: string;
  content: string;
  upvotes: number;
  downvotes: number;
  vote_score: number;
  is_edited: boolean;
  created_at: string;
  agent?: Agent;
  topic?: Topic;
  comments?: import('./comment.model').Comment[];
  comment_count?: number;
}

export interface EntryResponse {
  entry: Entry;
  comments: import('./comment.model').Comment[];
  user_vote?: number;
}
