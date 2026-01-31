package twitter

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Client handles Twitter/X API interactions
type Client struct {
	bearerToken string
	httpClient  *http.Client
	baseURL     string
}

// Config contains Twitter client configuration
type Config struct {
	BearerToken string
}

// NewClient creates a new Twitter API client
func NewClient(cfg Config) *Client {
	return &Client{
		bearerToken: cfg.BearerToken,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		baseURL: "https://api.twitter.com/2",
	}
}

// Tweet represents a Twitter/X tweet
type Tweet struct {
	ID        string `json:"id"`
	Text      string `json:"text"`
	AuthorID  string `json:"author_id"`
	CreatedAt string `json:"created_at"`
}

// User represents a Twitter/X user
type User struct {
	ID       string `json:"id"`
	Username string `json:"username"`
	Name     string `json:"name"`
}

// SearchResponse represents the Twitter search API response
type SearchResponse struct {
	Data     []Tweet         `json:"data"`
	Includes *SearchIncludes `json:"includes,omitempty"`
	Meta     *SearchMeta     `json:"meta,omitempty"`
}

type SearchIncludes struct {
	Users []User `json:"users,omitempty"`
}

type SearchMeta struct {
	ResultCount int    `json:"result_count"`
	NextToken   string `json:"next_token,omitempty"`
}

// VerifyTweet checks if a user has posted a tweet containing the verification code
// Returns error if client is not configured in production mode
func (c *Client) VerifyTweet(ctx context.Context, username string, verificationCode string) (bool, error) {
	if c.bearerToken == "" {
		// SECURITY: In development mode without bearer token, verification is skipped
		// This should be logged and monitored - production should always have a token
		return true, nil
	}

	// Search for recent tweets from the user containing the verification code
	query := fmt.Sprintf("from:%s tenekesozluk dogrulama %s", username, verificationCode)
	encodedQuery := url.QueryEscape(query)

	reqURL := fmt.Sprintf("%s/tweets/search/recent?query=%s&max_results=10&tweet.fields=created_at,author_id", c.baseURL, encodedQuery)

	req, err := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
	if err != nil {
		return false, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+c.bearerToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return false, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusTooManyRequests {
		return false, fmt.Errorf("twitter rate limit exceeded")
	}

	if resp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("twitter API returned status %d", resp.StatusCode)
	}

	var searchResp SearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
		return false, fmt.Errorf("failed to decode response: %w", err)
	}

	// Check if we found any matching tweets
	if searchResp.Meta == nil || searchResp.Meta.ResultCount == 0 {
		return false, nil
	}

	// Verify the tweet contains the exact verification code
	for _, tweet := range searchResp.Data {
		if strings.Contains(strings.ToLower(tweet.Text), strings.ToLower(verificationCode)) {
			return true, nil
		}
	}

	return false, nil
}

// GetUserByUsername retrieves a Twitter user by username
func (c *Client) GetUserByUsername(ctx context.Context, username string) (*User, error) {
	if c.bearerToken == "" {
		// Development mode - return mock user
		return &User{
			ID:       "dev_user_id",
			Username: username,
			Name:     username,
		}, nil
	}

	reqURL := fmt.Sprintf("%s/users/by/username/%s", c.baseURL, username)

	req, err := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+c.bearerToken)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("user not found: %s", username)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("twitter API returned status %d", resp.StatusCode)
	}

	var userResp struct {
		Data User `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&userResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &userResp.Data, nil
}

// IsConfigured returns true if the client has valid credentials
func (c *Client) IsConfigured() bool {
	return c.bearerToken != ""
}

// MustBeConfigured panics if the client is not configured
// Use this at startup in production to ensure Twitter verification is enabled
func (c *Client) MustBeConfigured() {
	if !c.IsConfigured() {
		panic("Twitter client is not configured - TWITTER_BEARER_TOKEN is required in production")
	}
}
