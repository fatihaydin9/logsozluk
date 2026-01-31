package topic

import (
	"context"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/tenekesozluk/api-gateway/internal/domain"
)

// Service handles topic-related business logic
type Service struct {
	topicRepo domain.TopicRepository
}

// NewService creates a new topic service
func NewService(topicRepo domain.TopicRepository) *Service {
	return &Service{
		topicRepo: topicRepo,
	}
}

// CreateInput contains the input for creating a topic
type CreateInput struct {
	Title     string
	Category  string
	Tags      []string
	CreatedBy *uuid.UUID
}

// Create creates a new topic
func (s *Service) Create(ctx context.Context, input CreateInput) (*domain.Topic, error) {
	// Validate title
	if len(input.Title) < 2 {
		return nil, domain.NewValidationError("title_too_short", "Title must be at least 2 characters", "title")
	}
	if len(input.Title) > 200 {
		return nil, domain.NewValidationError("title_too_long", "Title must be at most 200 characters", "title")
	}

	// Generate slug
	slug := domain.GenerateSlug(input.Title)

	// Check if slug already exists
	existing, _ := s.topicRepo.GetBySlug(ctx, slug)
	if existing != nil {
		return nil, domain.ErrTopicAlreadyExists
	}

	// Default category
	if input.Category == "" {
		input.Category = "general"
	}

	topic := &domain.Topic{
		ID:        uuid.New(),
		Slug:      slug,
		Title:     input.Title,
		Category:  input.Category,
		Tags:      input.Tags,
		CreatedBy: input.CreatedBy,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	if err := s.topicRepo.Create(ctx, topic); err != nil {
		return nil, domain.NewInternalError("create_failed", "Failed to create topic", err)
	}

	return topic, nil
}

// GetByID retrieves a topic by ID
func (s *Service) GetByID(ctx context.Context, id uuid.UUID) (*domain.Topic, error) {
	topic, err := s.topicRepo.GetByID(ctx, id)
	if err != nil {
		return nil, domain.ErrTopicNotFound
	}
	if topic.IsHidden {
		return nil, domain.ErrTopicNotFound
	}
	return topic, nil
}

// GetBySlug retrieves a topic by slug
func (s *Service) GetBySlug(ctx context.Context, slug string) (*domain.Topic, error) {
	topic, err := s.topicRepo.GetBySlug(ctx, slug)
	if err != nil {
		return nil, domain.ErrTopicNotFound
	}
	if topic.IsHidden {
		return nil, domain.ErrTopicNotFound
	}
	return topic, nil
}

// List retrieves a paginated list of topics
func (s *Service) List(ctx context.Context, limit, offset int) ([]*domain.Topic, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}
	return s.topicRepo.List(ctx, limit, offset)
}

// Search retrieves topics matching a query
func (s *Service) Search(ctx context.Context, query string, limit, offset int) ([]*domain.Topic, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	if offset < 0 {
		offset = 0
	}

	return s.topicRepo.Search(ctx, strings.TrimSpace(query), limit, offset)
}

// ListTrending retrieves trending topics (gündem)
func (s *Service) ListTrending(ctx context.Context, limit int) ([]*domain.Topic, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}
	return s.topicRepo.ListTrending(ctx, limit)
}
