package dto

// DebbeItem represents a DEBE entry in API responses
type DebbeItem struct {
	ID               string        `json:"id"`
	DebeDate         string        `json:"debe_date"`
	EntryID          string        `json:"entry_id"`
	Rank             int           `json:"rank"`
	ScoreAtSelection float64       `json:"score_at_selection"`
	Entry            *EntryResponse `json:"entry,omitempty"`
}

// DebbeResponse represents a DEBE list response
type DebbeResponse struct {
	Debbes []*DebbeItem `json:"debbes"`
	Date   string       `json:"date"`
}
