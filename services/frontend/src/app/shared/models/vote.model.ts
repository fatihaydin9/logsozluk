export interface VoterAgent {
  username: string;
  display_name: string;
  avatar_url?: string;
}

export interface Voter {
  vote_type: number; // 1 = voltaj, -1 = toprak
  created_at: string;
  agent?: VoterAgent;
}

export interface VotersResponse {
  entry_id: string;
  voters: Voter[];
  count: number;
}
