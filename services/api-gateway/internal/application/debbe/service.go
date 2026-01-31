package debbe

import (
	"context"
	"strings"
	"time"

	"github.com/logsozluk/api-gateway/internal/domain"
)

// Service handles debbe-related business logic
type Service struct {
	repo domain.DebbeRepository
}

// NewService creates a new debbe service
func NewService(repo domain.DebbeRepository) *Service {
	return &Service{repo: repo}
}

// GetLatest retrieves the latest DEBE list
func (s *Service) GetLatest(ctx context.Context) ([]*domain.Debbe, error) {
	return s.repo.GetLatest(ctx)
}

// GetByDate retrieves DEBE entries for a given date (YYYY-MM-DD)
func (s *Service) GetByDate(ctx context.Context, dateStr string) ([]*domain.Debbe, error) {
	clean := strings.TrimSpace(dateStr)
	if clean == "" {
		return nil, domain.NewValidationError("missing_date", "Date is required", "date")
	}

	parsed, err := time.Parse("2006-01-02", clean)
	if err != nil {
		return nil, domain.NewValidationError("invalid_date", "Date must be in YYYY-MM-DD format", "date")
	}

	return s.repo.GetByDate(ctx, parsed.Format("2006-01-02"))
}
