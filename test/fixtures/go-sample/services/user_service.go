package services

import (
	"errors"
	"os"
	"strconv"
	"time"

	"github.com/example/go-sample-project/models"
)

// HACK: Using in-memory store instead of database
var users = []models.User{
	{ID: "1", Name: "John Doe", Email: "john@example.com", CreatedAt: time.Now()},
	{ID: "2", Name: "Jane Smith", Email: "jane@example.com", CreatedAt: time.Now()},
}

// UserService provides user-related business logic
type UserService struct {
	apiBaseURL string
}

// NewUserService creates a new UserService
func NewUserService() *UserService {
	apiURL := os.Getenv("EXTERNAL_API_URL")
	if apiURL == "" {
		apiURL = "https://api.example.com"
	}
	return &UserService{apiBaseURL: apiURL}
}

// GetAllUsers returns all users
func (s *UserService) GetAllUsers() []models.User {
	return users
}

// GetUserByID returns a user by ID
func (s *UserService) GetUserByID(id string) (*models.User, error) {
	for _, user := range users {
		if user.ID == id {
			return &user, nil
		}
	}
	return nil, errors.New("user not found")
}

// CreateUser creates a new user
func (s *UserService) CreateUser(input models.CreateUserInput) models.User {
	newUser := models.User{
		ID:        strconv.Itoa(len(users) + 1),
		Name:      input.Name,
		Email:     input.Email,
		CreatedAt: time.Now(),
	}
	users = append(users, newUser)
	return newUser
}
