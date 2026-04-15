using UnityEngine;
using UnityEngine.Events;

public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    [Header("Settings")]
    public float matchDuration = 90f;

    [Header("Runtime")]
    public GameState State { get; private set; } = GameState.Menu;
    public float TimeLeft { get; private set; }
    public int   RoundWinner { get; private set; } // 1 = player, 2 = AI

    public UnityEvent OnMatchStart  = new UnityEvent();
    public UnityEvent OnMatchEnd    = new UnityEvent();
    public UnityEvent OnStateChange = new UnityEvent();

    Fighter _player;
    Fighter _ai;

    void Awake()
    {
        if (Instance != null) { Destroy(gameObject); return; }
        Instance = this;
    }

    void Start()
    {
        // Fighters are tagged "Player" and "AI"
        foreach (var f in FindObjectsOfType<Fighter>())
        {
            if (f.CompareTag("Player")) _player = f;
            else                        _ai      = f;
        }
    }

    void Update()
    {
        if (State != GameState.Playing) return;

        TimeLeft -= Time.deltaTime;

        if (TimeLeft <= 0f)
        {
            TimeLeft = 0f;
            EndMatch(DetermineWinnerByHP());
            return;
        }

        if (_player != null && _player.HP <= 0) { EndMatch(2); return; }
        if (_ai     != null && _ai.HP     <= 0) { EndMatch(1); return; }
    }

    // ── Public API ─────────────────────────────────────────────────────────────

    public void StartMatch()
    {
        TimeLeft = matchDuration;
        RoundWinner = 0;
        SetState(GameState.Playing);
        OnMatchStart.Invoke();
    }

    public void RetryMatch()
    {
        foreach (var f in FindObjectsOfType<Fighter>()) f.ResetFighter();
        StartMatch();
    }

    public void GoToMenu()
    {
        foreach (var f in FindObjectsOfType<Fighter>()) f.ResetFighter();
        SetState(GameState.Menu);
        OnStateChange.Invoke();
    }

    // ── Internals ──────────────────────────────────────────────────────────────

    void EndMatch(int winner)
    {
        RoundWinner = winner;
        SetState(GameState.GameOver);
        OnMatchEnd.Invoke();
    }

    int DetermineWinnerByHP()
    {
        if (_player == null || _ai == null) return 0;
        if (_player.HP > _ai.HP) return 1;
        if (_ai.HP > _player.HP) return 2;
        return 0; // draw
    }

    void SetState(GameState s)
    {
        State = s;
        OnStateChange.Invoke();
    }
}

public enum GameState { Menu, Playing, GameOver }
