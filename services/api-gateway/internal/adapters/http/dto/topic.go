package dto

import "time"

// CreateTopicRequest represents the topic creation request
type CreateTopicRequest struct {
	Title    string   `json:"title" binding:"required,min=2,max=200"`
	Category string   `json:"category" binding:"omitempty,max=50"`
	Tags     []string `json:"tags" binding:"omitempty,max=10,dive,max=30"`
}

// TopicResponse represents a topic in API responses
type TopicResponse struct {
	ID       string   `json:"id"`
	Slug     string   `json:"slug"`
	Title    string   `json:"title"`
	Category string   `json:"category"`
	Tags     []string `json:"tags,omitempty"`

	EntryCount     int `json:"entry_count"`
	TotalUpvotes   int `json:"total_upvotes"`
	TotalDownvotes int `json:"total_downvotes"`
	CommentCount   int `json:"comment_count"`

	TrendingScore float64 `json:"trending_score"`

	LastEntryAt *time.Time `json:"last_entry_at,omitempty"`

	VirtualDayPhase *string `json:"virtual_day_phase,omitempty"`

	IsLocked bool `json:"is_locked"`

	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// TopicDetailResponse represents a topic with entries
type TopicDetailResponse struct {
	Topic   *TopicResponse   `json:"topic"`
	Entries []*EntryResponse `json:"entries"`
}

// TopicEntriesResponse represents a topic with entries and pagination
type TopicEntriesResponse struct {
	Topic      *TopicResponse   `json:"topic"`
	Entries    []*EntryResponse `json:"entries"`
	Pagination *PaginationMeta  `json:"pagination"`
}

// GundemResponse represents the gündem (trending topics)
type GundemResponse struct {
	Topics     []*TopicResponse `json:"topics"`
	Pagination *PaginationMeta  `json:"pagination,omitempty"`
}

// TopicSearchResponse represents a topic search response
type TopicSearchResponse struct {
	Topics []*TopicResponse `json:"topics"`
}
