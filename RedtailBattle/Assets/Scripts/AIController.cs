using UnityEngine;

/// <summary>
/// Simple beatable AI: chases → attacks → retreats.
/// Cooldowns are 2× player, damage same as player, occasional misses.
/// </summary>
[RequireComponent(typeof(Fighter))]
public class AIController : MonoBehaviour
{
    [Header("AI Tuning")]
    [Range(0f, 1f)]
    public float missChance      = 0.28f;   // probability to miss an attack
    public float punchCooldownMul = 2.2f;   // AI cooldown multiplier vs player
    public float kickCooldownMul  = 2.2f;
    [Range(0f, 1f)]
    public float damageMul        = 0.55f;  // fraction of base damage AI deals

    [Header("Behaviour Distances")]
    public float attackDist   = 1.3f;
    public float retreatDist  = 0.8f;
    public float retreatSpeed = 2.5f;

    // State machine
    enum AIState { Chase, Attack, Retreat }
    AIState _state = AIState.Chase;

    Fighter _fighter;
    Fighter _target;

    float _actionTimer;
    float _retreatTimer;

    // How often AI evaluates (seconds)
    const float THINK_RATE = 0.25f;

    void Awake()
    {
        _fighter = GetComponent<Fighter>();

        // Scale up cooldowns to make AI beatable
        _fighter.punchCooldown *= punchCooldownMul;
        _fighter.kickCooldown  *= kickCooldownMul;
        // Scale down damage
        _fighter.punchDmg *= damageMul;
        _fighter.kickDmg  *= damageMul;
    }

    void Start()
    {
        foreach (var f in FindObjectsOfType<Fighter>())
        {
            if (f != _fighter) { _target = f; break; }
        }
    }

    void Update()
    {
        if (GameManager.Instance == null ||
            GameManager.Instance.State != GameState.Playing) return;

        if (_target == null) return;

        _actionTimer -= Time.deltaTime;
        if (_actionTimer > 0) return;
        _actionTimer = THINK_RATE;

        float dist = Mathf.Abs(transform.position.x - _target.transform.position.x);
        _fighter.FaceTarget(_target.transform);

        switch (_state)
        {
            case AIState.Chase:
                if (dist <= attackDist)
                {
                    _state = AIState.Attack;
                    _fighter.StopMoving();
                }
                else
                {
                    float dir = _target.transform.position.x > transform.position.x ? 1f : -1f;
                    _fighter.Move(dir * 0.7f); // slightly slower than player
                }
                break;

            case AIState.Attack:
                _fighter.StopMoving();
                if (dist > attackDist + 0.4f)
                {
                    _state = AIState.Chase;
                    break;
                }
                if (ShouldAttack())
                {
                    bool hitLanded = Random.value > missChance &&
                                     (Random.value > 0.5f
                                         ? _fighter.TryPunch(_target)
                                         : _fighter.TryKick(_target));
                    if (hitLanded)
                    {
                        _state = AIState.Retreat;
                        _retreatTimer = Random.Range(0.4f, 0.9f);
                    }
                }
                break;

            case AIState.Retreat:
                _retreatTimer -= THINK_RATE;
                float retreatDir = _target.transform.position.x > transform.position.x ? -1f : 1f;
                _fighter.Move(retreatDir);

                if (_retreatTimer <= 0 || dist > attackDist + 1.5f)
                    _state = AIState.Chase;
                break;
        }
    }

    bool ShouldAttack() => !_fighter.IsAttacking;
}
