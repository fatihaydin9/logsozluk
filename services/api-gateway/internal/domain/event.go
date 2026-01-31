package domain

import (
	"time"

	"github.com/google/uuid"
)

// Event status constants
const (
	EventStatusNew       = "new"
	EventStatusProcessed = "processed"
	EventStatusIgnored   = "ignored"
)

// Event represents a collected event from RSS/APIs
type Event struct {
	ID              uuid.UUID
	Source          string
	SourceURL       *string
	ExternalID      *string
	Title           string
	Description     *string
	ImageURL        *string
	ClusterID       *uuid.UUID
	ClusterKeywords []string
	Status          string
	ProcessedAt     *time.Time
	TopicID         *uuid.UUID
	CreatedAt       time.Time
}

// Debbe represents a DEBE (Dünün En Beğenilen Entry'leri) entry
type Debbe struct {
	ID               uuid.UUID
	DebeDate         time.Time
	EntryID          uuid.UUID
	Rank             int // 1-10
	ScoreAtSelection float64
	CreatedAt        time.Time

	// Joined fields (for queries)
	Entry *Entry
}
