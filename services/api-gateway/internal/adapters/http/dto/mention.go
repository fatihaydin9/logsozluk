package dto

type MentionValidateRequest struct {
	Content   string   `json:"content"`
	Mentions  []string `json:"mentions"`
}

type MentionValidateResponse struct {
	ProcessedContent string   `json:"processed_content"`
	ValidMentions    []string `json:"valid_mentions"`
	InvalidMentions  []string `json:"invalid_mentions"`
}

type MentionItemResponse struct {
	ID        string `json:"id"`
	IsRead    bool   `json:"is_read"`
	CreatedAt string `json:"created_at"`
	Source    string `json:"source"`
}

type MentionListResponse struct {
	Mentions []MentionItemResponse `json:"mentions"`
}

type MentionReadResponse struct {
	Message string `json:"message"`
}
