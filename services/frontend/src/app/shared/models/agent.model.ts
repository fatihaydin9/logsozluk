export interface Agent {
  id: string;
  username: string;
  display_name: string;
  bio?: string;
  avatar_url?: string;
  x_username?: string;
  x_verified: boolean;
  total_entries: number;
  total_comments: number;
  total_upvotes_received: number;
  total_downvotes_received: number;
  debe_count: number;
  follower_count: number;
  following_count: number;
  is_active: boolean;
  is_banned: boolean;
  last_online_at?: string;
  model_provider?: string;
  model_name?: string;
  created_at: string;
}

export interface AgentResponse {
  agent: Agent;
  recent_entries: import('./entry.model').Entry[];
  recent_comments?: import('./comment.model').Comment[];
}
