import { Agent } from './agent.model';

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
  replies?: Comment[];
}
