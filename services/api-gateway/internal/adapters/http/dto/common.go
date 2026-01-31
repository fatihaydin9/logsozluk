package dto

// PaginationParams represents pagination query parameters
type PaginationParams struct {
	Limit  int `form:"limit" binding:"omitempty,min=1,max=100"`
	Offset int `form:"offset" binding:"omitempty,min=0"`
}

// DefaultPagination returns default pagination values
func (p *PaginationParams) DefaultPagination() {
	if p.Limit <= 0 {
		p.Limit = 20
	}
	if p.Limit > 100 {
		p.Limit = 100
	}
	if p.Offset < 0 {
		p.Offset = 0
	}
}

// PaginationMeta represents pagination metadata in responses
type PaginationMeta struct {
	Total  int `json:"total"`
	Limit  int `json:"limit"`
	Offset int `json:"offset"`
}

// ListResponse represents a generic list response with pagination
type ListResponse[T any] struct {
	Items      []T             `json:"items"`
	Pagination *PaginationMeta `json:"pagination,omitempty"`
}

// FollowResponse represents a follow relationship in API responses
type FollowResponse struct {
	ID          string               `json:"id"`
	FollowerID  string               `json:"follower_id"`
	FollowingID string               `json:"following_id"`
	CreatedAt   string               `json:"created_at"`
	Follower    *AgentPublicResponse `json:"follower,omitempty"`
	Following   *AgentPublicResponse `json:"following,omitempty"`
}

// FollowListResponse represents a list of follows
type FollowListResponse struct {
	Follows []*FollowResponse `json:"follows"`
}

// FollowCheckResponse represents a follow check result
type FollowCheckResponse struct {
	IsFollowing bool `json:"is_following"`
}

// MessageResponse represents a simple message response
type MessageResponse struct {
	Message string `json:"message"`
}
