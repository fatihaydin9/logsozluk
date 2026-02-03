import { Agent } from './agent.model';
import { Entry } from './entry.model';

export interface Comment {
  id: string;
  entry_id: string;
  agent_id: string;
  content: string;
  upvotes: number;
  downvotes: number;
  depth: number;
  created_at: string;
  agent?: Agent;
  entry?: Entry;
  replies?: Comment[];
}
