import { Entry } from './entry.model';

export interface Debbe {
  id: string;
  debe_date: string;
  entry_id: string;
  rank: number;
  score_at_selection: number;
  entry?: Entry;
}

export interface DebbeResponse {
  debbes: Debbe[];
  date: string;
}
