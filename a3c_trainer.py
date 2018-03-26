import torch
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable

from generalsenv import GeneralEnvironment
from ActorCritic import ActorCritic

import gc


def ensure_shared_grads(model, shared_model):
    for param, shared_param in zip(model.parameters(),
                                   shared_model.parameters()):
        if shared_param.grad is not None:
            return
        shared_param._grad = param.grad


def train(rank, args, shared_model, optimizer=None):
    torch.manual_seed(args.seed + rank)

    env = GeneralEnvironment('policy.mdl')

    model = ActorCritic()

    if optimizer is None:
        optimizer = optim.Adam(shared_model.parameters(), lr=args.lr)

    model.train()

    state = env.reset()
    state = torch.Tensor(state)
    model.init_hidden(env.map_height, env.map_width)
    done = True

    episode_length = 0
    while True:
        # Sync with the shared model
        model.load_state_dict(shared_model.state_dict())

        values = []
        log_probs = []
        rewards = []
        entropies = []
        off_targets = []

        for step in range(args.num_steps):
            episode_length += 1
            value, logit = model(Variable(state.unsqueeze(0)))
            prob = F.softmax(logit)
            old_prob = prob

            # Set the probability of all items that not owned by user to
            # 0
            army_map = state[0, ...]
            label_map = (army_map > 0)
            label_map = label_map.view(1, env.map_height, env.map_width)
            label_map = label_map.expand(8, env.map_height, env.map_width)
            label_map = label_map.contiguous()
            label_map = label_map.view(-1)
            # prob[~label_map] = 0
            prob = old_prob * Variable(label_map.float())
            # Penalize model for predicting off target tiles
            off_prob = old_prob * Variable((~label_map).float())
            off_targets.append(off_prob.sum(1))

            log_prob = F.log_softmax(logit)
            entropy = -(log_prob * prob).sum(1)
            entropies.append(entropy)

            action = prob.multinomial().data
            log_prob = log_prob.gather(1, Variable(action))

            state, reward, done, _ = env.step(action.numpy().flat[0])
            done = done or episode_length >= args.max_episode_length

            if done:
                episode_length = 0
                state = env.reset()
                model.init_hidden(env.map_height, env.map_width)

            state = torch.Tensor(state)
            values.append(value)
            log_probs.append(log_prob)
            rewards.append(reward)

            if done:
                break

        R = torch.zeros(1, 1)
        if not done:
            value, _ = model(Variable(state.unsqueeze(0)))
            R = value.data

        values.append(Variable(R))
        policy_loss = 0
        value_loss = 0
        R = Variable(R)
        gae = torch.zeros(1, 1)
        for i in reversed(list(range(len(rewards)))):
            R = args.gamma * R + rewards[i]
            advantage = R - values[i]
            value_loss = value_loss + 0.5 * advantage.pow(2)

            # Generalized Advantage Estimataion
            delta_t = rewards[i] + args.gamma * \
                values[i + 1].data - values[i].data
            gae = gae * args.gamma * args.tau + delta_t

            policy_loss = policy_loss - \
                log_probs[i] * Variable(gae) - args.entropy_coef * entropies[i] + \
                args.off_tile_coef * off_targets[i]

        optimizer.zero_grad()
        loss = policy_loss + args.value_loss_coef * value_loss

        (loss).backward()
        torch.nn.utils.clip_grad_norm(model.parameters(), args.max_grad_norm)

        ensure_shared_grads(model, shared_model)
        optimizer.step()
        model.reset_hidden()
        gc.collect()
