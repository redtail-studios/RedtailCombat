using UnityEngine;

[RequireComponent(typeof(Rigidbody2D))]
public class Fighter : MonoBehaviour
{
    // ── Inspector ──────────────────────────────────────────────────────────────
    [Header("Stats")]
    public float maxHP      = 100f;
    public float moveSpeed  = 5f;
    public float punchDmg   = 8f;
    public float kickDmg    = 14f;
    public float punchRange = 1.4f;
    public float kickRange  = 1.8f;

    [Header("Cooldowns (seconds)")]
    public float punchCooldown = 0.40f;
    public float kickCooldown  = 0.70f;

    [Header("Visuals")]
    public Renderer bodyRenderer;   // main body (works with MeshRenderer or SpriteRenderer)
    public Renderer helmetRenderer; // helmet/head

    Color _originalBodyColor = Color.white;

    // ── Runtime ────────────────────────────────────────────────────────────────
    public float HP { get; private set; }
    public bool  IsAttacking { get; private set; }

    Rigidbody2D  _rb;
    float        _punchTimer;
    float        _kickTimer;
    bool         _facingRight = true;
    float        _startX;

    // ── Arena bounds (set by SceneBuilder) ────────────────────────────────────
    public static float ArenaLeft  = -3.8f;
    public static float ArenaRight =  3.8f;

    // ── Events (used by UIManager / effects) ──────────────────────────────────
    public System.Action<float> OnHPChanged;
    public System.Action        OnPunch;
    public System.Action        OnKick;
    public System.Action        OnHit;

    // ══════════════════════════════════════════════════════════════════════════

    void Awake()
    {
        _rb = GetComponent<Rigidbody2D>();
        _rb.gravityScale = 0f;
        _rb.constraints  = RigidbodyConstraints2D.FreezeRotation;
        HP = maxHP;
        _startX = transform.position.x;
    }

    void Update()
    {
        if (GameManager.Instance == null ||
            GameManager.Instance.State != GameState.Playing) return;

        _punchTimer -= Time.deltaTime;
        _kickTimer  -= Time.deltaTime;

        // Clamp to arena
        Vector3 p = transform.position;
        p.x = Mathf.Clamp(p.x, ArenaLeft, ArenaRight);
        transform.position = p;
    }

    // ── Movement ───────────────────────────────────────────────────────────────

    /// <summary>Move horizontally. dir: -1 left, +1 right.</summary>
    public void Move(float dir)
    {
        if (GameManager.Instance?.State != GameState.Playing) return;
        _rb.linearVelocity = new Vector2(dir * moveSpeed, _rb.linearVelocity.y);
        if (dir != 0) SetFacing(dir > 0);
    }

    public void StopMoving() => _rb.linearVelocity = new Vector2(0, _rb.linearVelocity.y);

    // ── Attacks ────────────────────────────────────────────────────────────────

    public bool TryPunch(Fighter target)
    {
        if (_punchTimer > 0 || target == null) return false;
        _punchTimer = punchCooldown;
        IsAttacking = true;
        OnPunch?.Invoke();
        Invoke(nameof(ResetAttack), 0.25f);

        float dist = Mathf.Abs(transform.position.x - target.transform.position.x);
        if (dist <= punchRange)
        {
            target.TakeDamage(punchDmg);
            return true;
        }
        return false;
    }

    public bool TryKick(Fighter target)
    {
        if (_kickTimer > 0 || target == null) return false;
        _kickTimer = kickCooldown;
        IsAttacking = true;
        OnKick?.Invoke();
        Invoke(nameof(ResetAttack), 0.35f);

        float dist = Mathf.Abs(transform.position.x - target.transform.position.x);
        if (dist <= kickRange)
        {
            target.TakeDamage(kickDmg);
            return true;
        }
        return false;
    }

    public void TakeDamage(float amount)
    {
        HP = Mathf.Max(0, HP - amount);
        OnHPChanged?.Invoke(HP);
        OnHit?.Invoke();
        FlashHit();
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    public void ResetFighter()
    {
        HP = maxHP;
        _punchTimer = 0; _kickTimer = 0;
        IsAttacking = false;
        transform.position = new Vector3(_startX, transform.position.y, 0);
        _rb.linearVelocity = Vector2.zero;
        OnHPChanged?.Invoke(HP);
        CancelInvoke();
    }

    void SetFacing(bool right)
    {
        if (_facingRight == right) return;
        _facingRight = right;
        Vector3 s = transform.localScale;
        s.x = right ? Mathf.Abs(s.x) : -Mathf.Abs(s.x);
        transform.localScale = s;
    }

    public void FaceTarget(Transform target)
    {
        SetFacing(target.position.x > transform.position.x);
    }

    void ResetAttack() => IsAttacking = false;

    void Awake_CacheColor()
    {
        if (bodyRenderer != null)
            _originalBodyColor = bodyRenderer.material.color;
    }

    void FlashHit()
    {
        if (bodyRenderer == null) return;
        _originalBodyColor = bodyRenderer.material.color;
        bodyRenderer.material.color = Color.white;
        Invoke(nameof(ResetColor), 0.1f);
    }

    void ResetColor()
    {
        if (bodyRenderer == null) return;
        bodyRenderer.material.color = _originalBodyColor;
    }
}
