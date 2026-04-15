using UnityEngine;
using UnityEngine.UI;
using TMPro;

/// <summary>
/// Manages all UI: HP bars, timer, menu panel, game-over panel, HUD.
/// Attach to a GameObject called "UIManager" in the scene.
/// </summary>
public class UIManager : MonoBehaviour
{
    [Header("HUD")]
    public Slider  playerHPBar;
    public Slider  aiHPBar;
    public TextMeshProUGUI timerText;
    public TextMeshProUGUI playerLabel;   // "YOU"
    public TextMeshProUGUI aiLabel;       // "RIVAL"
    public GameObject      hudPanel;

    [Header("Menu Panel")]
    public GameObject      menuPanel;
    public TextMeshProUGUI menuTitle;
    public Button          startButton;

    [Header("Game-Over Panel")]
    public GameObject      gameOverPanel;
    public TextMeshProUGUI resultText;    // "YOU WIN!" / "RIVAL WINS!" / "DRAW"
    public Button          retryButton;
    public Button          menuButton;

    GameManager _gm;

    void Start()
    {
        _gm = GameManager.Instance;

        if (_gm != null)
        {
            _gm.OnStateChange.AddListener(RefreshPanels);
            _gm.OnMatchEnd.AddListener(ShowGameOver);
        }

        // Wire up fighters
        foreach (var f in FindObjectsOfType<Fighter>())
        {
            if (f.CompareTag("Player"))
            {
                f.OnHPChanged += hp => SetBar(playerHPBar, hp, f.maxHP);
                SetBar(playerHPBar, f.HP, f.maxHP);
            }
            else
            {
                f.OnHPChanged += hp => SetBar(aiHPBar, hp, f.maxHP);
                SetBar(aiHPBar, f.HP, f.maxHP);
            }
        }

        // Wire up buttons
        startButton?.onClick.AddListener(() => _gm?.StartMatch());
        retryButton?.onClick.AddListener(() => _gm?.RetryMatch());
        menuButton? .onClick.AddListener(() => _gm?.GoToMenu());

        RefreshPanels();
    }

    void Update()
    {
        if (_gm?.State == GameState.Playing && timerText != null)
        {
            int secs = Mathf.CeilToInt(_gm.TimeLeft);
            timerText.text = secs.ToString("D2");
            timerText.color = secs <= 10 ? new Color(1f, 0.3f, 0.3f) : Color.white;
        }
    }

    void RefreshPanels()
    {
        if (_gm == null) return;

        bool isMenu    = _gm.State == GameState.Menu;
        bool isPlaying = _gm.State == GameState.Playing;
        bool isOver    = _gm.State == GameState.GameOver;

        menuPanel?.SetActive(isMenu);
        hudPanel? .SetActive(isPlaying || isOver);
        gameOverPanel?.SetActive(isOver);
    }

    void ShowGameOver()
    {
        if (resultText == null || _gm == null) return;
        switch (_gm.RoundWinner)
        {
            case 1:  resultText.text = "YOU WIN!";      resultText.color = new Color(0.2f, 1f, 0.4f); break;
            case 2:  resultText.text = "RIVAL WINS!";   resultText.color = new Color(1f, 0.3f, 0.3f); break;
            default: resultText.text = "DRAW";          resultText.color = Color.white; break;
        }
    }

    static void SetBar(Slider bar, float hp, float max)
    {
        if (bar != null) bar.value = max > 0 ? hp / max : 0;
    }
}
