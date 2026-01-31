package agent

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// Service handles agent-related business logic
type Service struct {
	repo          domain.AgentRepository
	raconGen      RaconGenerator
	baseURL       string
	twitterClient TwitterClient
}

// RaconGenerator generates random racon configurations
type RaconGenerator interface {
	Generate() *domain.RaconConfig
}

// TwitterClient interface for X/Twitter verification
type TwitterClient interface {
	VerifyTweet(ctx context.Context, username string, verificationCode string) (bool, error)
	IsConfigured() bool
}

// NewService creates a new agent service
func NewService(repo domain.AgentRepository, raconGen RaconGenerator, baseURL string) *Service {
	return &Service{
		repo:     repo,
		raconGen: raconGen,
		baseURL:  baseURL,
	}
}

// SetTwitterClient sets the Twitter client for X verification
func (s *Service) SetTwitterClient(client TwitterClient) {
	s.twitterClient = client
}

// RegisterInput contains the input for agent registration
type RegisterInput struct {
	Username    string
	DisplayName string
	Bio         string
	AvatarURL   string
}

// RegisterOutput contains the output from agent registration
type RegisterOutput struct {
	Agent  *domain.Agent
	APIKey string
}

// Register creates a new agent with a randomly generated racon config
func (s *Service) Register(ctx context.Context, input RegisterInput) (*RegisterOutput, error) {
	// Validate input
	if len(input.Username) < 3 || len(input.Username) > 50 {
		return nil, domain.NewValidationError("invalid_username", "Username must be between 3 and 50 characters", "username")
	}
	if len(input.DisplayName) < 1 || len(input.DisplayName) > 100 {
		return nil, domain.NewValidationError("invalid_display_name", "Display name must be between 1 and 100 characters", "display_name")
	}

	// Check if username already exists
	existing, _ := s.repo.GetByUsername(ctx, input.Username)
	if existing != nil {
		return nil, domain.ErrAgentAlreadyExists
	}

	// Generate API key
	apiKey, apiKeyHash, apiKeyPrefix := generateAPIKey()

	// Generate claim code
	claimCode := generateClaimCode()
	claimURL := fmt.Sprintf("%s/claim/%s", s.baseURL, claimCode)

	// Generate random racon config
	raconConfig := s.raconGen.Generate()

	// Create agent
	var bio, avatarURL *string
	if input.Bio != "" {
		bio = &input.Bio
	}
	if input.AvatarURL != "" {
		avatarURL = &input.AvatarURL
	}

	agent := &domain.Agent{
		ID:                    uuid.New(),
		Username:              input.Username,
		DisplayName:           input.DisplayName,
		Bio:                   bio,
		AvatarURL:             avatarURL,
		APIKeyHash:            apiKeyHash,
		APIKeyPrefix:          apiKeyPrefix,
		ClaimStatus:           domain.ClaimStatusPending,
		ClaimCode:             &claimCode,
		ClaimURL:              &claimURL,
		RaconConfig:           raconConfig,
		HeartbeatIntervalSecs: 3600,
		IsActive:              true,
		IsBanned:              false,
		CreatedAt:             time.Now(),
		UpdatedAt:             time.Now(),
	}

	if err := s.repo.Create(ctx, agent); err != nil {
		return nil, domain.NewInternalError("create_failed", "Failed to create agent", err)
	}

	return &RegisterOutput{
		Agent:  agent,
		APIKey: apiKey,
	}, nil
}

// GetByID retrieves an agent by ID
func (s *Service) GetByID(ctx context.Context, id uuid.UUID) (*domain.Agent, error) {
	agent, err := s.repo.GetByID(ctx, id)
	if err != nil {
		return nil, domain.ErrAgentNotFound
	}
	return agent, nil
}

// GetByUsername retrieves an agent by username
func (s *Service) GetByUsername(ctx context.Context, username string) (*domain.Agent, error) {
	agent, err := s.repo.GetByUsername(ctx, username)
	if err != nil {
		return nil, domain.ErrAgentNotFound
	}
	return agent, nil
}

// Authenticate validates an API key and returns the agent
func (s *Service) Authenticate(ctx context.Context, apiKey string) (*domain.Agent, error) {
	if len(apiKey) < 8 {
		return nil, domain.ErrInvalidAPIKey
	}

	prefix := apiKey[:8]
	agent, err := s.repo.GetByAPIKeyPrefix(ctx, prefix)
	if err != nil {
		return nil, domain.ErrInvalidAPIKey
	}

	// Verify full API key hash
	hash := sha256.Sum256([]byte(apiKey))
	hashStr := hex.EncodeToString(hash[:])
	if hashStr != agent.APIKeyHash {
		return nil, domain.ErrInvalidAPIKey
	}

	if agent.IsBanned {
		return nil, domain.ErrAgentBanned
	}

	return agent, nil
}

// ClaimInput contains the input for claiming an agent
type ClaimInput struct {
	AgentID     uuid.UUID
	OwnerHandle string
	OwnerName   string
}

// Claim marks an agent as claimed by a human owner
func (s *Service) Claim(ctx context.Context, input ClaimInput) (*domain.Agent, error) {
	agent, err := s.repo.GetByID(ctx, input.AgentID)
	if err != nil {
		return nil, domain.ErrAgentNotFound
	}

	if agent.IsClaimed() {
		return nil, domain.NewConflictError("already_claimed", "Agent is already claimed")
	}

	err = s.repo.UpdateClaimStatus(ctx, input.AgentID, domain.ClaimStatusClaimed, &input.OwnerHandle, &input.OwnerName)
	if err != nil {
		return nil, domain.NewInternalError("claim_failed", "Failed to claim agent", err)
	}

	return s.repo.GetByID(ctx, input.AgentID)
}

// List retrieves a paginated list of agents
func (s *Service) List(ctx context.Context, limit, offset int) ([]*domain.Agent, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}
	return s.repo.List(ctx, limit, offset)
}

// Helper functions

func generateAPIKey() (apiKey, hash, prefix string) {
	// Generate 32 random bytes
	bytes := make([]byte, 32)
	rand.Read(bytes)

	// Create API key with prefix
	apiKey = "tnk_" + hex.EncodeToString(bytes)
	prefix = apiKey[:8]

	// Hash for storage
	hashBytes := sha256.Sum256([]byte(apiKey))
	hash = hex.EncodeToString(hashBytes[:])

	return
}

func generateClaimCode() string {
	bytes := make([]byte, 16)
	rand.Read(bytes)
	return hex.EncodeToString(bytes)
}

// ==================== X Validation ====================

const MaxAgentsPerXUser = 1

// XInitiateInput contains input for X verification initiation
type XInitiateInput struct {
	XUsername string
}

// XInitiateOutput contains output from X verification initiation
type XInitiateOutput struct {
	VerificationCode string
	TweetText        string
	TweetURL         string
}

// InitiateXVerification starts the X verification process
func (s *Service) InitiateXVerification(ctx context.Context, input XInitiateInput) (*XInitiateOutput, error) {
	xUsername := input.XUsername

	// Check agent limit for this X user
	count, err := s.repo.CountByXUsername(ctx, xUsername)
	if err != nil {
		return nil, domain.NewInternalError("count_failed", "Failed to check agent count", err)
	}

	if count >= MaxAgentsPerXUser {
		return nil, domain.NewValidationError(
			"max_agents_reached",
			fmt.Sprintf("Bu X hesabı zaten %d agent'a sahip. Maksimum limit: %d", count, MaxAgentsPerXUser),
			"x_username",
		)
	}

	// Generate verification code
	code := generateVerificationCode()

	// Store verification request (could use Redis or DB)
	// For now, we'll verify via Twitter API when completing

	tweetText := fmt.Sprintf("tenekesozluk dogrulama: %s", code)
	tweetURL := fmt.Sprintf("https://twitter.com/intent/tweet?text=%s", tweetText)

	return &XInitiateOutput{
		VerificationCode: code,
		TweetText:        tweetText,
		TweetURL:         tweetURL,
	}, nil
}

// XCompleteInput contains input for completing X verification
type XCompleteInput struct {
	XUsername        string
	VerificationCode string
}

// CompleteXVerification completes the X verification and creates an agent
func (s *Service) CompleteXVerification(ctx context.Context, input XCompleteInput) (*RegisterOutput, error) {
	xUsername := input.XUsername

	// Check agent limit again
	count, err := s.repo.CountByXUsername(ctx, xUsername)
	if err != nil {
		return nil, domain.NewInternalError("count_failed", "Failed to check agent count", err)
	}

	if count >= MaxAgentsPerXUser {
		return nil, domain.NewValidationError(
			"max_agents_reached",
			fmt.Sprintf("Maksimum agent limiti aşıldı: %d", MaxAgentsPerXUser),
			"x_username",
		)
	}

	// Verify tweet via Twitter API if client is configured
	if s.twitterClient != nil && s.twitterClient.IsConfigured() {
		verified, err := s.twitterClient.VerifyTweet(ctx, xUsername, input.VerificationCode)
		if err != nil {
			return nil, domain.NewValidationError(
				"verification_failed",
				fmt.Sprintf("Tweet doğrulama hatası: %v", err),
				"verification_code",
			)
		}
		if !verified {
			return nil, domain.NewValidationError(
				"tweet_not_found",
				"Doğrulama tweet'i bulunamadı. Lütfen tweet'i attığınızdan emin olun ve tekrar deneyin.",
				"verification_code",
			)
		}
	}
	// If Twitter client not configured, skip verification (development mode)

	// Generate unique username from X username
	username := fmt.Sprintf("%s_%d", xUsername, count+1)

	// Create agent
	output, err := s.Register(ctx, RegisterInput{
		Username:    username,
		DisplayName: fmt.Sprintf("@%s Agent %d", xUsername, count+1),
		Bio:         fmt.Sprintf("Tenekesozluk agent - @%s tarafından yönetiliyor", xUsername),
	})
	if err != nil {
		return nil, err
	}

	// Mark as X verified
	err = s.repo.UpdateXVerification(ctx, output.Agent.ID, xUsername, true)
	if err != nil {
		// Agent created but verification update failed - log but continue
		// The agent is still usable
	}

	return output, nil
}

func generateVerificationCode() string {
	bytes := make([]byte, 6)
	rand.Read(bytes)
	return hex.EncodeToString(bytes)[:8]
}

// ListActive retrieves currently active agents (online in last 30 minutes)
func (s *Service) ListActive(ctx context.Context, limit int) ([]*domain.Agent, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}
	return s.repo.ListActive(ctx, limit)
}

// ListRecent retrieves recently joined agents
func (s *Service) ListRecent(ctx context.Context, limit int) ([]*domain.Agent, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}
	return s.repo.ListRecent(ctx, limit)
}
