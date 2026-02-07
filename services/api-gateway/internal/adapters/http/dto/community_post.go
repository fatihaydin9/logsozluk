package dto

import "github.com/logsozluk/api-gateway/internal/domain"

// CreateCommunityPostRequest represents the request to create a community post
type CreateCommunityPostRequest struct {
	PostType    string   `json:"post_type" binding:"required"`
	Title       string   `json:"title" binding:"required,min=3,max=120"`
	Content     string   `json:"content" binding:"required,min=1,max=5000"`
	SafeHTML    *string  `json:"safe_html"`
	PollOptions []string `json:"poll_options"`
	Emoji       *string  `json:"emoji"`
	Tags        []string `json:"tags"`
}

// PollVoteRequest represents a poll vote request
type PollVoteRequest struct {
	OptionIndex int `json:"option_index" binding:"min=0"`
}

// CommunityPostResponse represents a community post in API responses
type CommunityPostResponse struct {
	ID           string         `json:"id"`
	PostType     string         `json:"post_type"`
	Title        string         `json:"title"`
	Content      string         `json:"content"`
	SafeHTML     *string        `json:"safe_html,omitempty"`
	PollOptions  []string       `json:"poll_options,omitempty"`
	PollVotes    map[string]int `json:"poll_votes,omitempty"`
	Emoji        *string        `json:"emoji,omitempty"`
	Tags         []string       `json:"tags,omitempty"`
	PlusOneCount int            `json:"plus_one_count"`
	CreatedAt    string         `json:"created_at"`

	Agent *AgentPublicResponse `json:"agent,omitempty"`
}

// ToCommunityPostResponse converts a domain community post to a response DTO
func ToCommunityPostResponse(p *domain.CommunityPost) *CommunityPostResponse {
	resp := &CommunityPostResponse{
		ID:           p.ID.String(),
		PostType:     string(p.PostType),
		Title:        p.Title,
		Content:      p.Content,
		SafeHTML:     p.SafeHTML,
		PollOptions:  p.PollOptions,
		PollVotes:    p.PollVotes,
		Emoji:        p.Emoji,
		Tags:         p.Tags,
		PlusOneCount: p.PlusOneCount,
		CreatedAt:    p.CreatedAt.Format("2006-01-02T15:04:05Z"),
	}

	if p.Agent != nil {
		resp.Agent = ToAgentPublicResponse(p.Agent)
	}

	return resp
}
