using UnityEngine;

/// <summary>
/// Reads keyboard input and drives the player Fighter.
/// Keyboard map:
///   A / Left Arrow  → move left
///   D / Right Arrow → move right
///   Space           → punch
///   X / K           → kick
///   Enter           → start match (from menu) / retry (from game-over)
/// </summary>
[RequireComponent(typeof(Fighter))]
public class PlayerController : MonoBehaviour
{
    Fighter _fighter;
    Fighter _enemy;

    void Awake()
    {
        _fighter = GetComponent<Fighter>();
    }

    void Start()
    {
        // Find AI opponent
        foreach (var f in FindObjectsOfType<Fighter>())
        {
            if (f != _fighter) { _enemy = f; break; }
        }
    }

    void Update()
    {
        HandleMenuInput();

        if (GameManager.Instance == null ||
            GameManager.Instance.State != GameState.Playing) return;

        HandleMovement();
        HandleAttacks();
    }

    void HandleMenuInput()
    {
        if (!Input.GetKeyDown(KeyCode.Return) &&
            !Input.GetKeyDown(KeyCode.KeypadEnter)) return;

        if (GameManager.Instance == null) return;

        switch (GameManager.Instance.State)
        {
            case GameState.Menu:     GameManager.Instance.StartMatch(); break;
            case GameState.GameOver: GameManager.Instance.RetryMatch(); break;
        }
    }

    void HandleMovement()
    {
        float dir = 0f;

        if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow))
            dir = -1f;
        else if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow))
            dir = 1f;

        if (dir != 0)
            _fighter.Move(dir);
        else
            _fighter.StopMoving();
    }

    void HandleAttacks()
    {
        if (Input.GetKeyDown(KeyCode.Space))
            _fighter.TryPunch(_enemy);

        if (Input.GetKeyDown(KeyCode.X) || Input.GetKeyDown(KeyCode.K))
            _fighter.TryKick(_enemy);
    }

    // ── On-screen button hooks (called by UIManager buttons) ──────────────────

    public void OnPunchButton()  => _fighter.TryPunch(_enemy);
    public void OnKickButton()   => _fighter.TryKick(_enemy);
    public void OnLeftPressed()  => _fighter.Move(-1f);
    public void OnRightPressed() => _fighter.Move(1f);
    public void OnDirReleased()  => _fighter.StopMoving();
}
